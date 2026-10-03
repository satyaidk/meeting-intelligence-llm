# Testing guide

## The test pyramid

```text
            /\        live (1)       real Anthropic API, opt-in, costs money
           /  \       eval (6 cases) quality: precision / recall / F1
          /----\      integration    pipeline, review, API, CLI against a temp SQLite DB
         /      \
        /--------\    unit           pure functions: dates, names, grounding, scoring, parsing
```

Most tests are **unit** tests: fast (milliseconds), precise (a failure points
at one function), and need no database or network. **Integration** tests check
that the pieces work together. **Evaluation** measures *quality* of LLM
output, which unit tests cannot do. **Live** tests confirm the real API
integration still works.

| Folder | What | Speed |
|--------|------|-------|
| `tests/unit/` | `enrichment/`, `ingestion/`, extractors with fakes, metrics | ~1 s total |
| `tests/integration/` | `MeetingProcessor`, `ReviewService`, FastAPI `TestClient`, Typer `CliRunner` | a few seconds |
| `tests/integration/test_live_anthropic.py` | real API call; skipped unless `ACTIONGRAPH_LIVE_TESTS=1` | ~seconds, costs cents |

```bash
pytest                       # everything except live
pytest tests/unit -q         # just the fast ones
pytest --cov                 # with coverage
ACTIONGRAPH_LIVE_TESTS=1 pytest -m live      # PowerShell: $env:ACTIONGRAPH_LIVE_TESTS=1; pytest -m live
```

## How we test code that calls an LLM

LLM output is non-deterministic and costs money, so we separate two questions:

1. **Does *our* code behave correctly given some model output?** Deterministic, tested with fakes:
   - `FakeExtractor` (`tests/conftest.py`) returns hand-written `MeetingExtraction`s, so the whole pipeline is tested exactly.
   - `tests/unit/test_anthropic_extractor.py` passes a fake *client* to `AnthropicExtractor` to test request building, stop-reason handling and error translation without a network.
2. **Is the model's output *good*?** Measured, not asserted: `actiongraph eval` ([EVALUATION.md](EVALUATION.md)).

### Fakes vs. mocks
A **fake** is a small working implementation (our `FakeExtractor` really
returns results). A **mock** records calls and returns canned values for any
method. We prefer fakes: tests read like real usage and do not break when
internal call patterns change.

## Fixtures (`tests/conftest.py`)

| Fixture / helper | Gives you |
|------------------|-----------|
| `session` | A SQLAlchemy session on a fresh SQLite file in a temp folder |
| `offline_settings` | `Settings` with the offline extractor and the temp DB, ignoring your `.env` |
| `FakeExtractor(*extractions)` | Scripted extractor that also records the requests it received |
| `action()`, `decision()`, `risk()`, `update()`, `extraction()` | Short builders for schema objects |
| `MONDAY` | The reference meeting date (Mon 2026-09-07) |

## Writing a good test

- **Name says the behaviour:** `test_ambiguous_first_name_is_not_guessed`, not `test_resolver_3`.
- **Arrange / Act / Assert**, separated by blank lines.
- **One reason to fail.** Several asserts are fine if they check one behaviour.
- **Parametrise tables of cases** (`@pytest.mark.parametrize`): see `test_temporal.py`.
- **Inject time:** pass dates in (`today=...`) rather than calling `date.today()` inside logic.
- **No network, no shared state:** each test gets its own database.

## Coverage
Currently ~96% of lines. Coverage shows what is *not* tested; it does not
prove what *is* tested is correct. Do not write tests just to raise the
number. `speech_to_text.py` is excluded because it needs the optional Whisper
model.
