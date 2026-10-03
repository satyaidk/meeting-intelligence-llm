# 0001. Record architecture decisions

- Status: Accepted
- Date: 2026-10-03

## Context
ActionGraph combines several non-obvious choices (an LLM *plus* deterministic
post-processing, a graph stored in SQL, a human review step). Without a record,
the reasons behind these choices are lost, and future changes either repeat
old debates or undo good decisions by accident.

## Decision
We record each architecturally significant decision as a short Markdown ADR in
`docs/adr/`, using the template in `docs/adr/README.md`.

## Consequences
- Reviewers and newcomers can read the reasoning next to the code.
- Writing the "alternatives" section forces us to consider options before committing.
- Small cost: a few minutes per significant decision. Trivial choices do not get ADRs.

## Alternatives considered
- **Comments in code only:** good for local details, bad for cross-cutting decisions.
- **A wiki:** drifts away from the code and is not reviewed in pull requests.
