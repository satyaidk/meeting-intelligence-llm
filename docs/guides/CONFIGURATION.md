# Configuration reference

All settings are environment variables, read by `src/actiongraph/config.py`
(`Settings`, built on pydantic-settings). Values come from, in priority order:

1. real environment variables;
2. the `.env` file in the current directory;
3. the defaults below.

Invalid values (e.g. `ACTIONGRAPH_REVIEW_THRESHOLD=abc`) fail at start-up
with a clear validation error. CLI flags such as `--provider` and `--db`
override the corresponding setting for one command.

## LLM

| Variable | Default | Description |
|----------|---------|-------------|
| `ACTIONGRAPH_LLM_PROVIDER` | `anthropic` | `anthropic` (Claude) or `offline` (rule-based, free, no key). `.env.example` sets `offline`. |
| `ANTHROPIC_API_KEY` | – | Your API key. If unset, the SDK looks for other configured credentials. Stored as a `SecretStr` (never logged). |
| `ACTIONGRAPH_ANTHROPIC_MODEL` | `claude-opus-5-5` | Model id. |
| `ACTIONGRAPH_ANTHROPIC_EFFORT` | `medium` | `low` / `medium` / `high` / `xhigh` / `max`. Higher = more reasoning, more cost and latency. Tune with `actiongraph eval`. |
| `ACTIONGRAPH_ANTHROPIC_MAX_TOKENS` | `16000` | Output cap per request. Raise it if very long meetings report truncation. |
| `ACTIONGRAPH_ANTHROPIC_ENABLE_FALLBACK` | `true` | If the model declines a request, retry server-side on Anthropic's recommended fallback model. |

## Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `ACTIONGRAPH_DATABASE_URL` | `sqlite:///data/actiongraph.db` | Any SQLAlchemy URL. Relative SQLite paths are relative to the current directory; the folder is created automatically. PostgreSQL example: `postgresql+psycopg://user:pass@localhost/actiongraph` (install the driver). |

## Human-in-the-loop

| Variable | Default | Description |
|----------|---------|-------------|
| `ACTIONGRAPH_REVIEW_THRESHOLD` | `0.7` | Items with combined confidence below this go to review. Higher = fewer mistakes, more manual review. |

## Speech-to-text (requires `pip install -e ".[audio]"`)

| Variable | Default | Description |
|----------|---------|-------------|
| `ACTIONGRAPH_WHISPER_MODEL` | `base` | `tiny`, `base`, `small`, `medium`, `large-v3`. Bigger = more accurate, slower. |
| `ACTIONGRAPH_WHISPER_DEVICE` | `cpu` | `cpu` or `cuda` (NVIDIA GPU with CUDA installed). |

## Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `ACTIONGRAPH_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`. Set `ANTHROPIC_LOG=debug` to also see SDK request logs. |

## Adding a new setting

1. Add a typed field to `Settings` in `config.py` (with a default and, if needed, `Field(...)` constraints).
2. Document it in `.env.example` and in this file.
3. Read it where needed via the injected settings (API: `Depends(get_settings)`; CLI: `_settings()`), not via `os.environ`.
