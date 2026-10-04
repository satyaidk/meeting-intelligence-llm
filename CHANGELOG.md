# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Web UI deep links: `#review`, `#graph`, `#meetings`, `#actions/<id>` open a view directly.
- README banner, product screenshots and demo video link; `SECURITY.md` and `CODE_OF_CONDUCT.md`.

### Changed
- README restructured to a standard open-source layout (overview, demo, architecture, getting started, usage, quality, evaluation, ADRs).
- CI also runs on pushes to the `dev` branch.

### Fixed
- Graph view: decision and risk nodes were not drawn (an explicit `size: undefined` overrode the library default); the graph now zooms to fit once the layout settles.

## [0.1.0] - 2026-10-03

### Added
- Ingestion of `.txt/.md`, WebVTT, SRT and JSON transcripts; optional audio/video transcription with faster-whisper.
- LLM extraction with Claude using structured outputs (`MeetingExtraction` Pydantic schema), prompt caching on the system prompt and server-side refusal fallback.
- Offline rule-based extractor (`ACTIONGRAPH_LLM_PROVIDER=offline`) as a free baseline.
- Evidence grounding, entity resolution, deterministic deadline resolution and confidence-based review routing.
- Cross-meeting tracking: status and deadline updates as events, duplicate folding, superseding stale proposals, risk → blocked-action links.
- Review workflow: approve, reject, edit (API, CLI and UI).
- REST API (FastAPI), Typer CLI, single-page web UI with an interactive graph; Mermaid export.
- Evaluation harness (precision / recall / F1, owner and deadline accuracy, status-update F1) with six labelled cases including a held-out case.
- 160 automated tests; GitHub Actions CI; design doc, architecture docs, ADRs 0001–0007, concept explainers and guides.
