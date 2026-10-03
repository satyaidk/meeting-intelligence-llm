# Runbook

What to do when something goes wrong. Each entry: **symptom → likely cause → fix.**
Add an entry every time you solve a new problem; that is how runbooks grow.

## Quick diagnostics

```bash
actiongraph --help                         # is the CLI installed in this environment?
python -c "import actiongraph; print(actiongraph.__version__)"
curl http://127.0.0.1:8000/api/health      # is the server up, which provider/model?
ACTIONGRAPH_LOG_LEVEL=DEBUG actiongraph process file.txt   # verbose logs
ANTHROPIC_LOG=debug ...                     # also log SDK requests
```

## LLM / API

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Anthropic rejected the credentials` | Missing/invalid `ANTHROPIC_API_KEY` | Put a valid key in `.env` (no quotes needed); restart the server. Or use `--provider offline`. |
| `Model '…' was not found` | Typo or retired model id | Fix `ACTIONGRAPH_ANTHROPIC_MODEL`. |
| `Rate limited by the Anthropic API` | Too many requests/tokens per minute | Wait and retry; the SDK already retried twice. For bulk work, process sequentially or use the Batches API. |
| `Could not reach the Anthropic API` | Network/proxy/firewall | Check connectivity; set `HTTPS_PROXY` if behind a proxy. |
| `The output was truncated at max_tokens` | Very long meeting | Raise `ACTIONGRAPH_ANTHROPIC_MAX_TOKENS`. |
| `The model's output failed validation` | A value broke a schema rule (e.g. confidence > 1) | Retry; if it repeats, check the schema descriptions for contradictions. |
| `The model declined to process this transcript` | Safety refusal (rare for meetings) | Check the transcript content; fallback is already enabled by default. |
| HTTP 502 from `/api/meetings` | Any of the above, surfaced by the API | Read `detail` in the response body. |

## Data and storage

| Symptom | Cause | Fix |
|---------|-------|-----|
| `no such column` / odd errors after editing `models.py` | Schema changed; no migrations | Delete `data/*.db` (local data loss) or add the column manually. |
| `database is locked` | Two processes writing the same SQLite file | Stop the other process (e.g. a second `serve`). For concurrency, use PostgreSQL. |
| Demo shows old data | `serve` pointed at a different DB than `demo` | Use the same `--db` path for both. |
| Duplicate actions across meetings | Model re-created an open item with different wording/owner | Reject the duplicate in review; consider lowering `DUPLICATE_THRESHOLD` in `services/tracking.py` (measure first). |

## Input files

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Unsupported file type '.docx'` | Not an allowed extension | Export the transcript as `.txt` or `.vtt`. |
| `No speech found in …` | Empty file, or subtitles with no timing lines | Check the file; `.vtt/.srt` need `00:00:01.000 --> …` lines. |
| `… is not valid UTF-8 text` | File saved in another encoding | Re-save as UTF-8. |
| Owners missing for audio input | Whisper has no speaker names | Expected (see concepts/08). Name people in speech, or review the items. |
| `Audio/video input needs the optional dependency` | `faster-whisper` not installed | `pip install -e ".[audio]"`. |

## Web UI

| Symptom | Cause | Fix |
|---------|-------|-----|
| Graph tab says the library could not load | No internet (vis-network loads from a CDN) | Use "Copy as Mermaid" instead, or vendor the library into `web/`. |
| UI shows "API unreachable" | Server not running / wrong port | `actiongraph serve` and reload. |

## Cost control
- Each processed meeting is **one** API request; token usage is stored per meeting and printed by the CLI.
- Lower `ACTIONGRAPH_ANTHROPIC_EFFORT` for cheaper bulk processing, and confirm quality with `actiongraph eval`.
- Develop and test with `--provider offline` (free); switch to Claude for real runs.

## Security and privacy checklist
- `.env` is git-ignored; never paste keys into issues or logs.
- Transcripts contain personal data. They are stored in `data/` and sent only to the configured LLM provider. Delete `data/` to remove them.
- The server binds to `127.0.0.1` by default. Do **not** expose it to a network without adding authentication.
