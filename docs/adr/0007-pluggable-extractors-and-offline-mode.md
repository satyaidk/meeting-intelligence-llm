# 0007. Extractor interface with an offline rule-based implementation

- Status: Accepted
- Date: 2026-10-03

## Context
The pipeline needs an extractor, but: tests must not call a paid API;
learners may not have an API key; we want to *measure* the LLM's value
against something; and the LLM provider or model may change.

## Decision
Define `Extractor` as a `typing.Protocol` (`extraction/base.py`) with one
method, `extract(ExtractionRequest) -> ExtractionResult`. Provide:
- `AnthropicExtractor`: the production implementation (Claude);
- `RuleBasedExtractor`: a regex baseline, selected with `ACTIONGRAPH_LLM_PROVIDER=offline`;
- `FakeExtractor` (tests only): returns scripted results.

`build_extractor(settings)` chooses the implementation. The pipeline only
knows the interface.

## Consequences
- The whole system (pipeline, API, UI, CLI) runs and is tested with no network and no cost.
- `actiongraph eval` compares extractors on the same data, which turns "the LLM is better" into a measured claim.
- Adding a provider means one new class; no pipeline changes.
- The rule-based extractor is intentionally limited and must not be mistaken for a production fallback: its evaluation shows it collapses on natural speech (case 06).

## Alternatives considered
- **Mock the SDK in every test:** couples tests to SDK internals; breaks on SDK upgrades.
- **Record/replay real API responses (VCR-style):** realistic, but cassettes go stale and still need an initial paid run; a good addition later for the Anthropic adapter itself.
- **No offline mode:** simpler, but the project would be unusable without a key.
