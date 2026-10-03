# Evaluation guide

> Unit tests tell you the code works. Evaluation tells you the **model's
> output is good**. You need both, and you cannot replace one with the other.

## Why evaluate?
Changing a prompt, a schema description, the model or the effort level
changes extraction quality in ways you cannot predict by reading a few
outputs. "It looked better on the demo" is an anecdote. An evaluation is a
**fixed, labelled dataset + metrics**, run the same way every time, so changes
can be compared with numbers.

## Running it

```bash
actiongraph eval --provider offline      # rule-based baseline: free, instant
actiongraph eval --provider anthropic    # Claude: one API call per case
actiongraph eval --dataset path/to/other/cases
```

## The dataset (`evals/datasets/*.json`)
Each case is a meeting transcript with the answers a careful human would give:
expected actions (task, owner, due date), status updates on provided open
actions, decisions and risks. See [evals/README.md](../../evals/README.md) for
the format and what each case tests.

## Metrics

Predicted items are matched to expected ("gold") items one-to-one by text
similarity (greedy, highest similarity first, threshold 0.45). Then:

| Metric | Formula | Question it answers |
|--------|---------|---------------------|
| **Precision** | TP / (TP + FP) | Of what we extracted, how much was right? (low = invented items) |
| **Recall** | TP / (TP + FN) | Of what we should have found, how much did we find? (low = missed items) |
| **F1** | 2·P·R / (P + R) | One number balancing both |
| **Owner accuracy** | correct owners / matched actions | Given we found the action, is the owner right? |
| **Deadline accuracy** | correct dates / matched actions | …is the resolved due date right? (tests LLM phrase copying **and** our resolver together) |
| **Status-update F1** | matched by action id + accepted status | Is cross-meeting tracking right? |

TP = true positive (matched), FP = false positive (predicted, no gold match),
FN = false negative (gold item nobody predicted). Totals are **micro-averaged**:
TP/FP/FN are summed across cases before computing ratios, so bigger cases
count more.

**Which matters more here?** Precision. An invented action reaches a real
person; a missed one can be added in review. When two prompts tie on F1,
prefer the one with higher precision.

## Reading the baseline results: a lesson about overfitting

| Case | Offline action F1 |
|------|------------------:|
| 01–05 | 0.96 (micro-averaged over the five cases) |
| **06 held-out messy standup** | **0.00** |

The regex rules were written while looking at cases 01–05, so of course they
do well there. Case 06 was written afterwards in casual speech ("I'm on it",
"leave that with me") and the rules find *nothing*. This is **overfitting**:
performance on data you tuned on says little about new data.

Professional practice that follows from this:
- Keep a **held-out** set you never look at while tuning prompts or rules. Report it separately.
- Label cases **before** running any extractor on them; labelling from model output copies its mistakes into the "truth".
- Grow the dataset from **real failures** (rejected items in the review queue are perfect candidates).

## Known limitations of this harness
- **Small dataset.** Six cases can show large effects, not 2% improvements. Real teams use hundreds.
- **Lexical matching.** `similarity()` compares words, not meaning: "Implement auth changes" vs "Handle the authentication changes" scores below the threshold (there is a test documenting this). Upgrades: embeddings, or an LLM-as-judge prompt that decides whether two tasks are the same.
- **LLM variance.** The same prompt can score differently across runs. Run important comparisons more than once.
- **Cost.** Each anthropic run is one request per case; check the token counts in the CLI.

## A good prompt-change workflow
1. Run the eval on `main`; save the table.
2. Make one change.
3. Re-run; compare per-case, not just the total.
4. Look at the actual diffs for cases that got worse.
5. Put both tables in the pull request.
