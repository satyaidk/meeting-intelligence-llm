# 07. Cross-meeting tracking: state across conversations

## What it is
Reading each meeting **in the context of earlier ones**, so that "auth is
blocked" updates last week's "Priya will build auth" instead of creating a
new, disconnected note.

```text
Meeting 1  "Priya will handle the authentication changes"  -> Action #1 (open)
Meeting 2  "The authentication changes are blocked"        -> #1 open -> blocked
Meeting 3  "Authentication is completed"                   -> #1 blocked -> done
```

## Why it matters
This is the difference between a summariser and a tracker. Without it, every
meeting produces new items, nothing is ever closed, and the list becomes noise.

## How ActionGraph does it

**1. Give the model the open work.** Before extraction, the pipeline loads
every open action (not done/cancelled, not rejected, *including* items still
in review) and adds them to the prompt with their ids:

```text
<open_action_items>
- id=1 | task: Handle the authentication changes | owner: Priya Sharma | deadline: none | status: open
- id=3 | task: Share the user research | owner: Sam Lee | deadline: by Wednesday | status: open
</open_action_items>
```

The prompt explains *why* to report progress as `status_updates` instead
of new actions ("otherwise the tracker shows duplicates").

**2. Validate what comes back** (`services/pipeline.py`, stage 7):
- an update for an id we did not provide is **discarded** with a warning (the model invented it);
- a second update for the same id in one meeting is ignored;
- a "change" to the same status with no new deadline is recorded as `mentioned`, not as a change.

**3. Store history as events.** Every change is an `ActionEvent` with
`from_status`, `to_status`, the meeting it came from, and the evidence quote.
Reading an action's events gives its timeline (`actiongraph timeline 1`).

**4. Safety nets in code** (`services/tracking.py`):
- **De-duplication:** if the model still creates a "new" action that is ≥ 0.75 similar to an open action with the same owner, it becomes a `mentioned` event on the existing one.
- **Superseding:** when a newer update is applied, older pending proposals for the same action are marked `superseded`.
- **Risk linking:** a risk's `blocks_task` text is matched to the most similar action, creating a `BLOCKS` edge.

## Pitfalls
- The open-action list grows over time. For long-running teams, you would limit it (e.g. by recency or relevance search) to keep prompts small.
- Similarity-based matching is lexical; "auth" vs "authentication" can be missed. Embeddings are the natural upgrade.
- Postponements change a commitment; ActionGraph flags ambiguous new deadlines for review but applies clear ones automatically. Is that the right policy? (An open question in the design doc.)

## Try it
Run `actiongraph demo --provider offline` and read the "Cross-meeting
timelines" section. Then open the **Graph** tab in the UI and follow the
dashed `UPDATED` edges from meetings 2 and 3.
