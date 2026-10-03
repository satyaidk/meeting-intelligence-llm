# Contributing to ActionGraph

Thanks for helping! This file is the short version; the full workflow is in
[docs/guides/DEVELOPMENT.md](docs/guides/DEVELOPMENT.md).

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
cp .env.example .env
pytest
```

## Before you open a pull request

- [ ] `ruff check src tests` passes
- [ ] `ruff format --check src tests` passes (run `ruff format src tests` to fix)
- [ ] `pytest` passes, and new behaviour has tests
- [ ] Docs updated (README / guide / API reference / ADR for significant decisions)
- [ ] `CHANGELOG.md` has a line under **Unreleased**
- [ ] If you changed prompts, schema descriptions, model or effort: before/after `actiongraph eval` tables are in the PR description

## Conventions

- **Branches:** `feat/…`, `fix/…`, `docs/…`, `refactor/…`, `test/…`, `chore/…`
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/), e.g. `fix(temporal): handle "end of the weekend"`
- **Architecture:** respect the layer dependency rule ([ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md#2-layers)); keep logic out of routes and the CLI.
- **Decisions:** a choice that is hard to reverse or affects several modules gets an ADR in `docs/adr/`.
- **Secrets:** never commit `.env`, API keys, or real meeting transcripts containing personal data.

## Reporting bugs

Open an issue using the bug template. Include the command you ran, the full
error message, your OS and Python version, and (if possible) a minimal
transcript that reproduces the problem, with personal details removed.
