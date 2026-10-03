# 03. Grounding: catching hallucinations with evidence quotes

## What it is
A **hallucination** is model output that sounds right but is not supported
by the input, such as an action nobody agreed to or an owner nobody named.
**Grounding** means tying every claim to evidence in the source, so it can be
checked.

## Why it matters
In ActionGraph, a hallucinated action becomes a reminder in a real person's
task list. Structured outputs guarantee the *shape* of the data, not its
*truth*. We need a separate, cheap, automatic truth check.

## How ActionGraph does it
1. The schema requires an `evidence` field on every item: *"A short verbatim
   quote (one sentence) copied exactly from the transcript."*
2. `enrichment/grounding.py` checks whether that quote is really there:

   ```text
   normalise both texts (lower-case, no punctuation, collapsed spaces)
   if quote in transcript:                          score = 1.0
   else:
       find the longest exact run of quote words in the transcript
       look at a window around it and count quote words that appear in order
       score = matched words / quote words
   grounded = score >= 0.8
   ```

   Tolerant enough for "we'll, um, update" vs "we'll update" (≈0.86), strict
   enough to reject an invented sentence (< 0.5).
3. `enrichment/confidence.py` uses the result: if not grounded, the item's
   confidence is capped at the grounding score and a reason is added:
   *"Evidence quote not found in the transcript (match 31%); the model may have
   paraphrased or invented it."*

## Why quotes and not just "trust the confidence"?
Models are not perfectly calibrated about their own mistakes. A verbatim
quote turns "do you believe the model?" into "can code find this string?",
which is objective, instant and free.

## Pitfalls
- Grounding proves the quote exists, not that the *interpretation* is right ("Sam, can you share the research?" exists, but is Sam the owner? Probably. Is the deadline correct? A separate check.)
- Audio transcripts contain recognition errors; the model may "correct" them in its quote, which lowers the score. The 0.8 threshold leaves room for that.
- Very short quotes ("Yes.") are trivially grounded and say little. The prompt asks for a full sentence.

## Try it
In `tests/unit/test_grounding.py`, add a case where the quote changes one
important word ("Friday" → "Monday"). What score does it get? Should that be
grounded? This is exactly the kind of design question to discuss in an interview.

Related: [06. Human-in-the-loop](06-human-in-the-loop.md)
