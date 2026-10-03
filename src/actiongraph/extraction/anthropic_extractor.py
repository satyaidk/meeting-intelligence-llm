"""LLM extraction with Claude, using structured outputs.

What happens in ``extract()``:

1. Build the request: a cached system prompt + a user message holding the
   transcript and context from earlier meetings.
2. Call ``client.beta.messages.parse(output_format=MeetingExtraction)``. The
   SDK turns the Pydantic model into a JSON schema; the API then *guarantees*
   the reply matches it, and the SDK validates it back into Python objects.
3. Check *why* the model stopped (``stop_reason``) before trusting the output.
4. Translate SDK exceptions into our own ``ExtractionError`` with advice the
   user can act on.

Why the ``beta`` namespace? Only to opt into server-side *fallbacks*: if the
model declines a request, the API re-runs it on Anthropic's recommended
fallback model within the same call. Set
``ACTIONGRAPH_ANTHROPIC_ENABLE_FALLBACK=false`` to turn that off.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import anthropic
import pydantic

from actiongraph.config import Settings
from actiongraph.domain.schemas import MeetingExtraction
from actiongraph.errors import ExtractionError, ExtractionRefusedError
from actiongraph.extraction.base import ExtractionRequest, ExtractionResult, TokenUsage
from actiongraph.extraction.prompts import SYSTEM_PROMPT, build_user_message

logger = logging.getLogger(__name__)

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicExtractor:
    name = "anthropic"

    def __init__(
        self,
        client: anthropic.Anthropic,
        *,
        model: str,
        effort: str = "medium",
        max_tokens: int = 16000,
        enable_fallback: bool = True,
    ) -> None:
        self._client = client
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        self.enable_fallback = enable_fallback

    @classmethod
    def from_settings(cls, settings: Settings) -> AnthropicExtractor:
        # With no explicit key the SDK looks for credentials itself
        # (ANTHROPIC_API_KEY env var, or a profile from `ant auth login`).
        key = settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else None
        client = anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()
        return cls(
            client,
            model=settings.anthropic_model,
            effort=settings.anthropic_effort,
            max_tokens=settings.anthropic_max_tokens,
            enable_fallback=settings.anthropic_enable_fallback,
        )

    def build_request_kwargs(self, request: ExtractionRequest) -> dict[str, Any]:
        """Everything sent to the API, as plain data (handy for tests and debugging)."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            # A list of blocks lets us mark the system prompt for prompt caching.
            # (Caching only kicks in once the cached prefix passes the model's
            # minimum size, so short prompts are simply not cached - no error.)
            "system": [
                {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
            ],
            "messages": [{"role": "user", "content": build_user_message(request)}],
            "output_format": MeetingExtraction,
            # Effort trades depth of reasoning for cost/latency. Extraction is a
            # moderately hard reading task, so "medium" is a sensible default.
            "output_config": {"effort": self.effort},
        }
        if self.enable_fallback:
            kwargs["betas"] = [FALLBACK_BETA]
            kwargs["fallbacks"] = "default"
        return kwargs

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        started = time.perf_counter()
        try:
            response = self._client.beta.messages.parse(**self.build_request_kwargs(request))
        except anthropic.AuthenticationError as exc:
            raise ExtractionError(
                "Anthropic rejected the credentials. Put a valid ANTHROPIC_API_KEY in .env, "
                "or run with ACTIONGRAPH_LLM_PROVIDER=offline."
            ) from exc
        except anthropic.PermissionDeniedError as exc:
            raise ExtractionError(f"This API key cannot use model '{self.model}'.") from exc
        except anthropic.NotFoundError as exc:
            raise ExtractionError(
                f"Model '{self.model}' was not found. Check ACTIONGRAPH_ANTHROPIC_MODEL."
            ) from exc
        except anthropic.RateLimitError as exc:
            raise ExtractionError(
                "Rate limited by the Anthropic API (the SDK already retried). Try again shortly."
            ) from exc
        except anthropic.BadRequestError as exc:
            raise ExtractionError(f"The API rejected the request: {exc.message}") from exc
        except anthropic.APIStatusError as exc:
            raise ExtractionError(
                f"Anthropic API error {exc.status_code} (request id {exc.request_id})."
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise ExtractionError("Could not reach the Anthropic API. Check your network.") from exc
        except pydantic.ValidationError as exc:
            # Structured outputs guarantee the JSON *shape*; Pydantic can still
            # reject *values* (e.g. confidence 1.4), or a reply cut off at max_tokens.
            raise ExtractionError(
                f"The model's output failed validation ({exc.error_count()} errors). If the "
                "transcript is very long, raise ACTIONGRAPH_ANTHROPIC_MAX_TOKENS."
            ) from exc
        except anthropic.AnthropicError as exc:  # e.g. no credentials configured at all
            raise ExtractionError(f"Anthropic client error: {exc}") from exc

        latency = time.perf_counter() - started

        # Always check why the model stopped before reading its output.
        if response.stop_reason == "refusal":
            raise ExtractionRefusedError(
                "The model declined to process this transcript (stop_reason=refusal)."
            )
        if response.stop_reason == "max_tokens":
            raise ExtractionError(
                "The output was truncated at max_tokens; raise ACTIONGRAPH_ANTHROPIC_MAX_TOKENS."
            )
        extraction = response.parsed_output
        if extraction is None:
            raise ExtractionError(
                f"No structured output returned (stop_reason={response.stop_reason})."
            )

        usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_read_input_tokens=response.usage.cache_read_input_tokens or 0,
            cache_creation_input_tokens=response.usage.cache_creation_input_tokens or 0,
        )
        logger.info(
            "Claude extraction: model=%s in=%d out=%d cached=%d latency=%.1fs",
            response.model,
            usage.input_tokens,
            usage.output_tokens,
            usage.cache_read_input_tokens,
            latency,
        )
        return ExtractionResult(
            extraction=extraction,
            provider=self.name,
            model=response.model,  # may differ from self.model if a fallback served it
            latency_seconds=round(latency, 2),
            usage=usage,
        )
