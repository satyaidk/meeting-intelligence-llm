"""The Claude extractor, tested WITHOUT calling the real API.

We hand the extractor a fake client object that records the request and
returns a canned response. This tests our code (request building, stop-reason
handling, error translation) for free, in milliseconds, with no network.
The real API is exercised by tests/integration/test_live_anthropic.py.
"""

from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2
import pytest

from actiongraph.domain.schemas import MeetingExtraction
from actiongraph.errors import ExtractionError, ExtractionRefusedError
from actiongraph.extraction.anthropic_extractor import FALLBACK_BETA, AnthropicExtractor
from actiongraph.extraction.base import ExtractionRequest, OpenAction
from actiongraph.extraction.prompts import SYSTEM_PROMPT
from tests.conftest import MONDAY, action, extraction

REQUEST = ExtractionRequest(
    transcript="Maya: Priya will handle the authentication changes.",
    meeting_date=MONDAY,
    meeting_title="Planning",
    open_actions=[OpenAction(7, "Share the user research", "Sam Lee", "by Wednesday", "open")],
    known_people=["Priya Sharma"],
)


class FakeMessages:
    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.response, self.error = response, error
        self.calls: list[dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def fake_client(messages: FakeMessages) -> Any:
    return SimpleNamespace(beta=SimpleNamespace(messages=messages))


def fake_response(stop_reason: str = "end_turn", parsed: MeetingExtraction | None = None) -> Any:
    usage = SimpleNamespace(
        input_tokens=1200,
        output_tokens=300,
        cache_read_input_tokens=1000,
        cache_creation_input_tokens=None,
    )
    return SimpleNamespace(
        stop_reason=stop_reason, parsed_output=parsed, usage=usage, model="claude-opus-5-5"
    )


def make_extractor(messages: FakeMessages, **kwargs: Any) -> AnthropicExtractor:
    return AnthropicExtractor(fake_client(messages), model="claude-opus-5-5", **kwargs)


def _api_error(cls: type[anthropic.APIStatusError], status: int) -> anthropic.APIStatusError:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("error", response=httpx2.Response(status, request=request), body=None)


# ---------------------------------------------------------------- requests
def test_request_uses_structured_outputs_and_cached_system_prompt() -> None:
    kwargs = make_extractor(FakeMessages()).build_request_kwargs(REQUEST)

    assert kwargs["model"] == "claude-opus-5-5"
    assert kwargs["output_format"] is MeetingExtraction
    assert kwargs["output_config"] == {"effort": "medium"}
    assert kwargs["system"][0]["text"] == SYSTEM_PROMPT
    assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_user_message_contains_transcript_and_context() -> None:
    kwargs = make_extractor(FakeMessages()).build_request_kwargs(REQUEST)
    message = kwargs["messages"][0]["content"]

    assert "<transcript>\nMaya: Priya will handle" in message
    assert "2026-09-07 (Monday)" in message  # weekday helps the model reason about dates
    assert "id=7 | task: Share the user research" in message
    assert "Priya Sharma" in message


def test_fallback_is_opt_out() -> None:
    with_fallback = make_extractor(FakeMessages()).build_request_kwargs(REQUEST)
    assert with_fallback["betas"] == [FALLBACK_BETA]
    assert with_fallback["fallbacks"] == "default"

    without = make_extractor(FakeMessages(), enable_fallback=False).build_request_kwargs(REQUEST)
    assert "betas" not in without
    assert "fallbacks" not in without


# --------------------------------------------------------------- responses
def test_successful_extraction() -> None:
    parsed = extraction(actions=[action("Handle auth", "Priya", "Priya will handle...")])
    messages = FakeMessages(fake_response(parsed=parsed))

    result = make_extractor(messages).extract(REQUEST)

    assert result.extraction is parsed
    assert result.provider == "anthropic"
    assert result.model == "claude-opus-5-5"
    assert result.usage.input_tokens == 1200
    assert result.usage.cache_read_input_tokens == 1000
    assert result.usage.cache_creation_input_tokens == 0  # None -> 0
    assert len(messages.calls) == 1


def test_refusal_is_reported() -> None:
    messages = FakeMessages(fake_response(stop_reason="refusal"))
    with pytest.raises(ExtractionRefusedError):
        make_extractor(messages).extract(REQUEST)


def test_truncated_output_is_reported() -> None:
    messages = FakeMessages(fake_response(stop_reason="max_tokens", parsed=extraction()))
    with pytest.raises(ExtractionError, match="max_tokens"):
        make_extractor(messages).extract(REQUEST)


# ------------------------------------------------------------------ errors
@pytest.mark.parametrize(
    ("error", "message"),
    [
        (_api_error(anthropic.AuthenticationError, 401), "ANTHROPIC_API_KEY"),
        (_api_error(anthropic.NotFoundError, 404), "ACTIONGRAPH_ANTHROPIC_MODEL"),
        (_api_error(anthropic.RateLimitError, 429), "Rate limited"),
        (_api_error(anthropic.InternalServerError, 500), "error 500"),
        (
            anthropic.APIConnectionError(
                request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
            ),
            "network",
        ),
    ],
)
def test_sdk_errors_become_helpful_extraction_errors(error: Exception, message: str) -> None:
    with pytest.raises(ExtractionError, match=message):
        make_extractor(FakeMessages(error=error)).extract(REQUEST)
