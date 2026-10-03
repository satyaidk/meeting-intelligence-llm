# REST API reference

Base URL: `http://127.0.0.1:8000/api` (start with `actiongraph serve`).
Interactive, always-up-to-date docs generated from the code: **`/docs`**
(Swagger UI) and **`/redoc`**. The OpenAPI schema is at `/openapi.json`.

All bodies are JSON unless noted. Dates are ISO `YYYY-MM-DD`.

## Errors

Every expected error has the same shape:

```json
{"detail": "Action item 42 not found", "error": "NotFoundError"}
```

| Status | When |
|--------|------|
| 400 | Unreadable/empty transcript file (`IngestionError`) |
| 404 | Unknown id (`NotFoundError`) |
| 409 | Valid request, wrong state, e.g. approving a stale update, nothing to change (`InvalidOperationError`) |
| 415 | Unsupported upload type (`UnsupportedFileTypeError`) |
| 422 | Request validation failed (FastAPI; `detail` is a list) **or** the model declined (`ExtractionRefusedError`) |
| 502 | The LLM provider failed (`ExtractionError`) |

## Health

### `GET /health`
```json
{"status": "ok", "version": "0.1.0", "llm_provider": "anthropic", "model": "claude-opus-5-5"}
```

## Meetings

### `POST /meetings`: process a pasted transcript
```json
{
  "title": "Sprint 14 Planning",
  "meeting_date": "2026-09-07",
  "transcript": "Maya Chen: Priya will handle the authentication changes.\nMaya Chen: Sam, please share the user research by Wednesday."
}
```
**201** → processing report:
```json
{
  "meeting_id": 1, "provider": "anthropic", "model": "claude-opus-5-5", "latency_seconds": 12.3,
  "usage": {"input_tokens": 2100, "output_tokens": 900, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
  "actions_created": 2, "decisions_created": 0, "risks_created": 0,
  "status_updates_applied": 0, "status_updates_pending": 0, "duplicates_merged": 0,
  "items_needing_review": 0, "warnings": []
}
```
(Numbers illustrative.)

### `POST /meetings/upload`: process a file (multipart form)
| Field | Type | Notes |
|-------|------|-------|
| `file` | file | `.txt .md .vtt .srt .json` or audio/video `.mp3 .wav .m4a .ogg .flac .mp4 .mov .mkv .webm` |
| `title` | string | required |
| `meeting_date` | date | required |

**201** → processing report (as above).

### `GET /meetings`
List of meetings (id, title, meeting_date, source, provider, model, latency).

### `GET /meetings/{id}`
One meeting with `summary`, `participants`, `transcript`, `llm_usage`, and the
`actions`, `decisions`, `risks` it created plus `status_updates` it made to
earlier actions.

## Actions

### `GET /actions`
Query parameters (all optional): `status` (`open | in_progress | blocked | done | cancelled`),
`owner_id`, `review_status` (`auto_approved | needs_review | approved | rejected | superseded`).
Rejected actions are hidden unless you filter for them.

```json
[{
  "id": 2, "meeting_id": 1, "task": "Update the API design",
  "owner": "Team", "owner_id": null, "owner_raw": "Team",
  "deadline_text": "by Friday", "due_date": "2026-09-11",
  "status": "done", "confidence": 0.9, "evidence": "We'll update the API design by Friday ...",
  "review_status": "auto_approved", "review_reasons": [],
  "created_at": "...", "updated_at": "..."
}]
```

### `GET /actions/{id}`
The action plus `events` (its timeline across meetings) and `blocking_risks`.

```json
"events": [
  {"event_type": "created", "meeting_title": "Sprint 14 Planning", "to_status": "open", "applied": true, "...": "..."},
  {"event_type": "status_changed", "meeting_title": "Sprint 14 Sync", "from_status": "open", "to_status": "blocked", "applied": true}
]
```

### `PATCH /actions/{id}`: human correction (counts as approval)
Any subset of:
```json
{"task": "Implement OAuth 2.0 login", "owner": "Priya", "deadline": "2026-10-02", "status": "in_progress"}
```
`owner` and `deadline` accept natural language (`"next Friday"` is resolved
relative to *today*). `""` clears owner/deadline. Ambiguous owners or
unparseable deadlines → **409**. Returns the updated action with events.

## Review queue

### `GET /review`
```json
{"total": 3, "actions": [...], "decisions": [...], "risks": [...], "events": [...]}
```
Every item includes `review_reasons`, e.g.
`"Deadline 'next Friday' was read as Fri 02 Oct 2026 (...); please confirm."`

### `POST /review/{kind}/{id}/approve`
### `POST /review/{kind}/{id}/reject`
`kind` is `action | decision | risk | event`. Approving an `event` (a pending
status update) applies it to its action. Response:
```json
{"kind": "event", "id": 11, "review_status": "approved"}
```

## People

### `GET /people`
```json
[{"id": 2, "display_name": "Priya Sharma", "aliases": ["priya", "priya s", "priya sharma"], "open_actions": 1}]
```

## Graph

### `GET /graph`
```json
{
  "nodes": [{"id": "meeting:1", "type": "meeting", "label": "07 Sep: Sprint 14 Planning", "data": {...}},
            {"id": "action:1", "type": "action", "label": "Handle the authentication changes", "data": {"status": "done", ...}}],
  "edges": [{"source": "meeting:1", "target": "action:1", "type": "CREATED", "label": ""},
            {"source": "risk:2", "target": "action:1", "type": "BLOCKS", "label": ""}]
}
```
Edge types: `CREATED`, `UPDATED`, `DECIDED`, `RAISED`, `OWNED_BY`, `MADE_BY`, `BLOCKS`.

### `GET /graph/mermaid`
`text/plain` Mermaid flowchart; paste it into a ```` ```mermaid ```` block on GitHub.

## Examples

**curl (macOS/Linux/Git Bash)**
```bash
curl -s -X POST http://127.0.0.1:8000/api/meetings \
  -H "Content-Type: application/json" \
  -d '{"title":"Sync","meeting_date":"2026-10-05","transcript":"Ana: I will send the deck by Friday."}'

curl -s -F "file=@samples/other_formats/design-review.vtt" -F "title=Design Review" \
  -F "meeting_date=2026-09-22" http://127.0.0.1:8000/api/meetings/upload
```

**PowerShell**
```powershell
$body = @{ title = "Sync"; meeting_date = "2026-10-05"; transcript = "Ana: I will send the deck by Friday." } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/meetings -ContentType "application/json" -Body $body
Invoke-RestMethod http://127.0.0.1:8000/api/review
```
