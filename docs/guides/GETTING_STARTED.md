# Getting started

From a fresh machine to a running ActionGraph in about 10 minutes.

## 1. Prerequisites

| Tool | Version | Check with |
|------|---------|-----------|
| Python | 3.11 or newer | `python --version` (Windows: `py -3.12 --version`) |
| Git | any recent | `git --version` |
| An Anthropic API key | optional | only for real LLM extraction |

## 2. Get the code and create a virtual environment

A **virtual environment** (`.venv`) is a private copy of Python for this
project, so its packages do not conflict with other projects.

**Windows (PowerShell)**
```powershell
cd "path\to\LLM Project"
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```
If PowerShell refuses to run the activation script, run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

**macOS / Linux / Git Bash**
```bash
cd "path/to/LLM Project"
python3 -m venv .venv
source .venv/bin/activate          # Git Bash on Windows: source .venv/Scripts/activate
```

Your prompt now starts with `(.venv)`. Activate it in every new terminal.

## 3. Install

```bash
pip install -e ".[dev]"            # app + test/lint tools
pip install -e ".[audio]"          # optional: Whisper for audio/video files
```

`-e` ("editable") means code changes take effect without reinstalling.
`.[dev]` installs the optional `dev` dependency group from `pyproject.toml`.

## 4. Configure

```bash
cp .env.example .env               # PowerShell: Copy-Item .env.example .env
```

The default `.env` uses the **offline** extractor, so nothing else is needed
to try the system. To use Claude, edit `.env`:

```ini
ACTIONGRAPH_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...       # from platform.claude.com -> API keys
```

Never commit `.env`; it is already in `.gitignore`. All settings are explained in
[CONFIGURATION.md](CONFIGURATION.md).

## 5. First run

```bash
actiongraph demo --provider offline     # 3 sample meetings, prints timelines
actiongraph review --db data/demo.db    # items waiting for a human
pytest                                  # all tests should pass
```

Then start the web UI on the demo data:

```bash
actiongraph serve --db data/demo.db
```

Open http://127.0.0.1:8000 (UI) and http://127.0.0.1:8000/docs (interactive API docs).
Stop the server with `Ctrl+C`.

## 6. With a real LLM

```bash
actiongraph demo --provider anthropic
actiongraph eval --provider anthropic   # quality on the labelled dataset (a few cents)
```

## 7. Process your own meeting

```bash
actiongraph process path/to/2026-10-05_team-sync.txt          # date taken from the file name
actiongraph process recording.m4a --date 2026-10-05 --title "Team sync"
```

Transcript format: one turn per line, `Speaker Name: what they said`.
Exports from Zoom/Teams (`.vtt`) work as-is.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `actiongraph: command not found` | Activate the venv; or run `python -m actiongraph ...` |
| `Anthropic rejected the credentials` | Check `ANTHROPIC_API_KEY` in `.env`, or use `--provider offline` |
| `Audio/video input needs the optional dependency` | `pip install -e ".[audio]"` |
| `No .txt transcripts found in samples/transcripts` | Run `demo` from the project root folder |
| Strange errors after changing `models.py` | Delete `data/*.db` (no migrations yet) |

More in the [runbook](../operations/RUNBOOK.md).
