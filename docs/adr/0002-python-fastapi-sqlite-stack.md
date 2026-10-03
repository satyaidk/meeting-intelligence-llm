# 0002. Python + FastAPI + SQLAlchemy/SQLite as the base stack

- Status: Accepted
- Date: 2026-10-03

## Context
We need: an LLM SDK, audio transcription, a JSON API, a database, a CLI, and
tests, built and understood by a beginner, runnable on Windows/macOS/Linux
without installing servers.

## Decision
- **Python 3.11+**: the language of the LLM and speech-to-text ecosystem (official `anthropic` SDK, `faster-whisper`).
- **Pydantic v2**: one model definition serves as the LLM's JSON schema, request validation and response serialisation.
- **FastAPI**: type-hint-driven routing, automatic validation and OpenAPI docs at `/docs`.
- **SQLAlchemy 2.0 ORM + SQLite**: a real relational database in a single file; switching to PostgreSQL is a URL change.
- **Typer + Rich** for the CLI; **pytest + ruff** for quality.

## Consequences
- Zero infrastructure: `pip install -e ".[dev]"` and everything runs.
- The same Pydantic skills transfer between the LLM contract and the API layer.
- SQLite allows only one writer at a time. Fine for one user; a multi-user deployment should move to PostgreSQL (see [ARCHITECTURE.md §7](../architecture/ARCHITECTURE.md#7-scaling-path-not-needed-yet)).
- No migrations yet (`create_all`); schema changes during development mean deleting the local DB.

## Alternatives considered
- **Node.js/TypeScript:** good SDK support, weaker local speech-to-text and data tooling.
- **Django:** batteries included, but more framework to learn than this project needs.
- **Flask:** simpler, but manual validation and docs that FastAPI gives for free.
- **PostgreSQL from day one:** adds a server to install for every learner.
