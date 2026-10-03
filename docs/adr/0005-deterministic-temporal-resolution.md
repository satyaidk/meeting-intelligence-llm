# 0005. LLM copies deadline phrases; code resolves dates

- Status: Accepted
- Date: 2026-10-03

## Context
Deadlines are spoken relative to the meeting: "by Friday", "end of next
week", "in two weeks". Turning them into dates needs the meeting date and
calendar arithmetic. Language models can do this but occasionally pick the
wrong week or month length, and the mistake looks plausible. A wrong date is
worse than no date, because it triggers reminders at the wrong time.

## Decision
The schema field is `deadline_text`: the model copies the phrase verbatim and
is told not to convert it. `enrichment/temporal.py` resolves it with an
ordered list of rules relative to the meeting date, returning
`(due_date, confidence, rule)`. Ambiguous phrases get confidence < 0.7 (→
review); event-relative phrases ("before the next release") stay unresolved
(→ review).

## Consequences
- Date resolution is deterministic, free, instant and fully unit-tested (`tests/unit/test_temporal.py`).
- Every date comes with an explanation a reviewer can check ("'next Friday' read as Friday of next week").
- The resolver only knows the phrases we wrote rules for. New phrasing needs a new rule and test. Unknown phrases fail *safe* (unresolved → review), never wrong.
- The original phrase is stored next to the date, so nothing is lost.

## Alternatives considered
- **LLM outputs ISO dates:** fewer rules to maintain, but silent errors and no explanation.
- **A date-parsing library (e.g. `dateparser`):** broad coverage, but less control over ambiguous cases and no confidence score; a reasonable future upgrade *behind the same function signature*.
- **Both, then compare:** doubles complexity for a small gain at this stage.
