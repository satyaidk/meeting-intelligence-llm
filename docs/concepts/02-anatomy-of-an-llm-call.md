# 02. Anatomy of an LLM call

A walk through the single request ActionGraph makes per meeting
(`AnthropicExtractor.build_request_kwargs` and `extract`).

```python
client.beta.messages.parse(
    model="claude-opus-5-5",
    max_tokens=16000,
    system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
    messages=[{"role": "user", "content": "<transcript>...</transcript> ..."}],
    output_format=MeetingExtraction,
    output_config={"effort": "medium"},
    betas=["server-side-fallback-2026-07-01"],
    fallbacks="default",
)
```

| Parameter | What it does | Our choice and why |
|-----------|--------------|--------------------|
| `model` | Which model answers | `claude-opus-5-5`, configurable via `ACTIONGRAPH_ANTHROPIC_MODEL` |
| `max_tokens` | Hard cap on the *output* length | 16 000: plenty for a long meeting; hitting it is detected (`stop_reason == "max_tokens"`) |
| `system` | Instructions that frame the whole conversation | The stable extraction instructions ([prompts.py](../../src/actiongraph/extraction/prompts.py)) |
| `messages` | The conversation; here a single user turn | Transcript + meeting date + known people + open actions |
| `output_format` | Structured outputs ([01](01-structured-outputs.md)) | `MeetingExtraction` |
| `output_config.effort` | How much the model reasons before answering (`low` … `max`) | `medium`: a good cost/quality balance for reading comprehension; tune with evals |
| `fallbacks` (beta) | If the model declines, the API retries on a recommended fallback model | On by default; `ACTIONGRAPH_ANTHROPIC_ENABLE_FALLBACK=false` to disable |

## Tokens and cost
Models read and write **tokens** (roughly ¾ of an English word each).
You pay per input token and per output token. The response's `usage`
tells you exactly what was used; ActionGraph stores it per meeting
(`meetings.llm_usage`) and prints it in the CLI. Typical meeting transcripts
are a few thousand tokens.

## Prompt caching
The beginning of a request (the *prefix*) can be cached by the API, and
cached input is billed at a fraction of the normal price on later requests.
Caching is a **prefix match**: any change early in the request invalidates
everything after it. That is why:
- the system prompt is identical for every meeting (no dates or ids in it), and
- everything that varies (transcript, date, open actions) goes in the user message *after* it.

Caching only applies once the cached prefix exceeds a model-specific minimum
length; a short prefix is simply not cached (no error). Check
`usage.cache_read_input_tokens` to see whether it happened.

## Stop reasons: always check *why* the model stopped
| `stop_reason` | Meaning | Our handling |
|---------------|---------|--------------|
| `end_turn` | Finished normally | Use the output |
| `max_tokens` | Hit the output cap; output is incomplete | Raise `ExtractionError` |
| `refusal` | The model declined | Raise `ExtractionRefusedError` (after any server-side fallback) |

## Errors and retries
The SDK automatically retries connection errors, 408/409/429 and 5xx
responses with exponential backoff (2 retries by default). We translate what
remains into our own errors with an actionable message, e.g.
`AuthenticationError` → "Put a valid ANTHROPIC_API_KEY in .env, or run with
ACTIONGRAPH_LLM_PROVIDER=offline." Catching specific exception classes (not
one broad `except`) keeps retryable and non-retryable failures distinct.

## Pitfalls
- Never hard-code API keys; ActionGraph reads them from the environment as a `SecretStr`.
- Do not put timestamps or random ids in the system prompt; they silently break caching.
- Do not assume the model that answered is the one you asked for when fallbacks are on: record `response.model` (we do).

## Try it
With a key configured, process the same meeting twice and compare the
`usage` printed by the CLI. Then lower `ACTIONGRAPH_ANTHROPIC_EFFORT` to `low`
and run `actiongraph eval` to see whether quality holds at lower cost.
