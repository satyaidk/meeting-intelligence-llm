# Prompt engineering guide

The prompt lives in `src/actiongraph/extraction/prompts.py`; the output
format lives in `src/actiongraph/domain/schemas.py`. Together they are the
"program" the model runs. This guide explains each design choice and how to
change it safely.

## The request at a glance

```text
system:  SYSTEM_PROMPT                     <- stable, identical for every meeting (cacheable)
user:    <transcript> ... </transcript>    <- long data first
         <meeting> title, date (weekday) </meeting>
         <known_people> ... </known_people>
         <open_action_items> id | task | owner | deadline | status </open_action_items>
         Extract the decisions, new action items, ...   <- the task last
format:  JSON schema generated from MeetingExtraction (structured outputs)
```

## Design choices, and why

| Choice | Why |
|--------|-----|
| **Stable system prompt; variable data in the user turn** | Prompt caching is a prefix match. Putting dates or transcripts in the system prompt would make every request's prefix unique. |
| **State the goal and the stakes first** ("precision matters more than coverage: … an invented one erodes trust") | Models make better judgement calls when they know *what the output is for*, not just what to output. |
| **Explain rules with reasons** ("report a status update instead of a new action … otherwise the tracker shows duplicates") | Reasons generalise to cases the rule did not mention; bare rules (especially in ALL CAPS) tend to be over-applied. |
| **Define fuzzy terms** (what is and is not an action item) | "Action item" means different things to different people; the definition is the spec. |
| **XML tags around data** | Clear boundaries between instructions and data; the model will not confuse a transcript line with an instruction. |
| **Long data first, task last** | Tends to improve quality on long inputs. |
| **Weekday next to the date** (`2026-09-07 (Monday)`) | Helps the model reason about "Friday" even though code resolves the date. |
| **Known people list** | Encourages consistent spelling; code still does the real entity resolution. |
| **Open items with ids** | Lets the model reference existing work, and lets code reject ids it never supplied. |
| **Ask for verbatim evidence and calibrated confidence** | Inputs to grounding and review routing. The prompt explains that low confidence is a *good* outcome when unsure, so the model is not pushed to over-claim. |
| **Treat the transcript as untrusted** | Defends against prompt injection ("ignore previous instructions…"), tested by eval case 05. |
| **No output format in the prompt text** | The JSON schema already enforces it; repeating it wastes tokens and can conflict. |

## Schema descriptions are prompt text too
Every `Field(description=...)` in `schemas.py` is sent to the model. For
example the `owner` description tells the model to resolve "I'll" to the
speaker and to use "Team" for "we". When you edit a description, treat it as
a prompt change and run the evaluation.

## How to change the prompt safely
1. Write down the failure you want to fix, with a concrete transcript line (add it as an eval case if it is not covered).
2. Run `actiongraph eval --provider anthropic` and save the results.
3. Make **one** change. Prefer adding a reason or a definition over adding a rule.
4. Re-run the eval; check the target case improved and no other case regressed.
5. Commit the prompt change with both result tables in the PR.

## Anti-patterns to avoid
- **Shouting** (`YOU MUST NEVER…`): causes over-correction; explain the reason instead.
- **Dumping every edge case into the prompt:** fix systematic issues in code (e.g. date maths) and keep the prompt about judgement.
- **Asking the model to "show its reasoning" in the output:** wasteful; the model already reasons internally (controlled by `effort`).
- **Volatile text in the system prompt** (timestamps, ids): silently disables caching.
- **Tuning on your test set:** you will overfit. Keep a held-out case.

## Knobs besides wording
| Knob | Where | Effect |
|------|-------|--------|
| `ACTIONGRAPH_ANTHROPIC_EFFORT` | `.env` | More reasoning → usually better on hard transcripts, more cost/latency |
| `ACTIONGRAPH_ANTHROPIC_MODEL` | `.env` | Different capability/cost trade-off |
| Schema shape | `schemas.py` | Adding/removing fields changes what the model attends to |
| Review threshold | `.env` | Does not change the model; changes how much reaches humans |
