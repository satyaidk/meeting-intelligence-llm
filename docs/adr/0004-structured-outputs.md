# 0004. Use structured outputs with a Pydantic schema for LLM extraction

- Status: Accepted
- Date: 2026-10-03

## Context
The extractor's output goes straight into a database. Free-text replies, or
JSON "requested" in the prompt, can be malformed, wrapped in prose, missing
fields or use the wrong types. Each of these needs repair code, retries, and
tests for every failure shape.

## Decision
Define the output as Pydantic models (`domain/schemas.py`) and call
`client.beta.messages.parse(output_format=MeetingExtraction, ...)`. The SDK
converts the model to a JSON schema; the API constrains generation to that
schema; the SDK validates the reply back into Pydantic objects
(`response.parsed_output`).

Schema conventions:
- Every field is required; optional values are `type | None` (explicit `null`).
- `Field(description=...)` text is written for the model, as part of the prompt.
- Constraints the API cannot enforce (e.g. `0 <= confidence <= 1`) are still declared; the SDK moves them into the description and Pydantic enforces them after the reply.

## Consequences
- No JSON parsing or repair code anywhere in the project.
- The schema is the single source of truth: changing it changes what the model is asked for and what our code receives.
- We must still check `stop_reason` (a `max_tokens` cut-off or a refusal means there is no valid output) and handle Pydantic `ValidationError` for value-level violations.
- Prompt and schema changes are code changes: reviewed, tested, versioned.

## Alternatives considered
- **"Reply in JSON" in the prompt + `json.loads`:** works most of the time; "most" is not good enough for a database.
- **Tool use with a forced tool call:** historically used for JSON; on current models forced `tool_choice` is not supported, and structured outputs is the purpose-built feature.
- **Several smaller calls (one per item type):** more cost and latency, and loses cross-item context.
