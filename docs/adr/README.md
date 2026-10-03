# Architecture Decision Records (ADRs)

An ADR captures **one** significant decision: the situation that forced it,
what we chose, and what that choice costs us. Teams write them so that a new
engineer (or you, in six months) can understand *why* the code looks the way
it does, without archaeology through old chat threads.

Rules we follow:
- One decision per record, numbered in order, never renumbered.
- Once **Accepted**, an ADR is not edited (except typos). If the decision
  changes, write a new ADR that **supersedes** it and update the old one's status.
- Short is good. One page is typical.

| # | Decision | Status |
|---|----------|--------|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-python-fastapi-sqlite-stack.md) | Python + FastAPI + SQLAlchemy/SQLite as the base stack | Accepted |
| [0003](0003-relational-storage-for-the-graph.md) | Store the graph in relational tables, not a graph database | Accepted |
| [0004](0004-structured-outputs.md) | Use structured outputs with a Pydantic schema for LLM extraction | Accepted |
| [0005](0005-deterministic-temporal-resolution.md) | LLM copies deadline phrases; code resolves dates | Accepted |
| [0006](0006-confidence-based-human-review.md) | Route uncertain items to human review using explicit reasons | Accepted |
| [0007](0007-pluggable-extractors-and-offline-mode.md) | Extractor interface with an offline rule-based implementation | Accepted |

## Template

```markdown
# NNNN. Title in the imperative ("Use X for Y")

- Status: Proposed | Accepted | Superseded by NNNN
- Date: YYYY-MM-DD

## Context
What is the situation and the forces at play (requirements, constraints, trade-offs)?

## Decision
What we decided, stated plainly.

## Consequences
Positive, negative and neutral results of the decision, including follow-up work.

## Alternatives considered
Each option and why it was not chosen.
```
