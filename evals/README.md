# Evaluation dataset

A small, hand-labelled ("golden") dataset for measuring extraction quality.
See [docs/guides/EVALUATION.md](../docs/guides/EVALUATION.md) for the method
and how to read the numbers.

```bash
actiongraph eval --provider offline      # free, instant: the rule-based baseline
actiongraph eval --provider anthropic    # real LLM: costs a few cents per run
```

| Case | Tests |
|------|-------|
| `01_sprint_planning` | owner patterns, team ownership, a hedged non-action |
| `02_sprint_sync` | status updates on open items (done / blocked / in progress / postponed) |
| `03_sprint_review` | completions, explicit vs. ambiguous vs. unresolvable dates |
| `04_design_review_vtt` | WebVTT input with `<v Speaker>` tags |
| `05_brainstorm_adversarial` | precision: ideas, past work, questions and a prompt-injection line are *not* actions |

## Adding a case

1. Put the transcript in `evals/transcripts/` (or reuse one from `samples/`).
2. Copy an existing JSON file, change `id`, `title`, `meeting_date`, `transcript`.
3. Label what a careful human would extract - **not** what the model currently
   outputs. Labelling from model output bakes its mistakes into the "truth".
4. Write a `notes` line saying what the case is meant to test.
