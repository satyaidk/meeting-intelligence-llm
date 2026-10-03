## What and why

<!-- One or two sentences: what does this change and what problem does it solve? Link the issue. -->

## How

<!-- The approach, and anything a reviewer should look at first. -->

## Testing

- [ ] New/changed behaviour is covered by tests
- [ ] `pytest` passes locally
- [ ] `ruff check` and `ruff format --check` pass

## LLM behaviour changes (prompt, schema descriptions, model, effort)

<!-- Delete if not applicable. Paste `actiongraph eval --provider anthropic` before and after. -->

| | Action F1 | Owner acc | Deadline acc | Update F1 |
|---|---|---|---|---|
| before | | | | |
| after | | | | |

## Docs

- [ ] README / guides / API reference updated where behaviour changed
- [ ] ADR added for a significant decision
- [ ] `CHANGELOG.md` updated under **Unreleased**
