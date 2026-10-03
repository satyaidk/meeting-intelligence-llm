# 0006. Route uncertain items to human review using explicit reasons

- Status: Accepted
- Date: 2026-10-03

## Context
Extracted actions become reminders sent to real people. A false positive
("you owe X by Friday" when nobody agreed to that) damages trust much more
than a false negative (a missed item someone adds by hand). Yet asking a human
to confirm *everything* defeats the purpose of automation.

## Decision
Every extracted item gets a `ReviewDecision` from `enrichment/confidence.py`:
- **auto_approved** only if *all* checks pass: LLM confidence ≥ threshold
  (`ACTIONGRAPH_REVIEW_THRESHOLD`, default 0.7), evidence grounded, owner
  resolved unambiguously, stated deadline resolved with confidence ≥ 0.7;
- otherwise **needs_review**, with one plain-English reason per failed check.

Status updates that need review are stored as unapplied `ActionEvent`s and
change nothing until approved. The model's self-reported confidence is
treated as one signal among several, never trusted alone, and it is capped by
the grounding score.

## Consequences
- Reviewers see *why* each item is in the queue, which makes review fast.
- The threshold is a single, tunable knob for the precision/review-workload trade-off.
- "Any reason → review" is simple to reason about and test; it may over-flag in some cases (e.g. a fuzzy-but-correct name match). That is acceptable for v0.1.
- Rejections are kept (not deleted) and can become evaluation data.

## Alternatives considered
- **Auto-accept everything:** simplest, but mistakes go straight to people's task lists.
- **Weighted score from all signals:** one number hides *which* check failed and needs tuning data we do not have yet.
- **A second LLM call to verify each item:** possible future improvement; costs more and still needs a human fallback.
