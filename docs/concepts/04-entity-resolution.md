# 04. Entity resolution: many names, one person

## What it is
**Entity resolution** (also "record linkage" or "deduplication") decides
when different references point to the same real-world thing. In meetings:

```text
"Priya"   "Priya S."   "@priya"   "priya.sharma@acme.com"   "Priya Sharma"   ->  one person
```

## Why it matters
Without it, the tracker shows five "people" with one task each, nobody's
workload is visible, and cross-meeting updates attach to the wrong record.

## How ActionGraph does it (`enrichment/entity_resolution.py`)

**Step 1, normalise** every spelling to a comparable key:

| Raw | Normalised |
|-----|-----------|
| `@Priya.Sharma` | `priya sharma` |
| `priya.sharma@acme.com` | `priya sharma` |
| `Priya S.` | `priya s` |
| `Dr. Sam Lee` | `sam lee` |

**Step 2, walk a ladder of rules**, from most to least certain; the first match wins:

| Rule | Example | Confidence |
|------|---------|-----------|
| Team words | "we", "team", "everyone" → owned by the team | 1.0 |
| Exact alias | `priya s` was seen before | 1.0 |
| Compatible name | first names equal, later tokens equal or initials: `priya s` ~ `priya sharma` | 0.9 |
| Fuzzy spelling | `pryia sharma` ~ `priya sharma` (similarity ≥ 0.8) | similarity × 0.9 (≈0.82 here) → **review** |
| New person | nobody matches | 0.85 |

**Step 3, refuse to guess.** If a rule matches *more than one* person
(two Priyas), the result is `AMBIGUOUS` with the candidate names, and the
item goes to review: *"Owner 'Priya' is ambiguous: could be Priya Kumar, Priya
Sharma."* A wrong assignment is worse than an unassigned one.

**Step 4, learn.** Every matched spelling is saved as an alias
(`person_aliases` table), and the display name upgrades to the most complete
form seen ("Priya" → "Priya Sharma"). Speakers are registered *first* in each
meeting, so "Priya" mentioned in passing resolves to the speaker "Priya Sharma".

Also note the **LLM's role**: the prompt lists known people and asks the
model to use those spellings when the reference is clear. The model handles
context ("she" / "I'll do it" → the speaker); code handles identity.

## Pitfalls
- Nicknames ("Bob" / "Robert") are not handled; they would need a nickname table or a human merge.
- "Compatible with *every* multi-word alias" prevents "Priya Kumar" from merging into a person already known as "Priya Sharma". Read `_is_compatible` and its test.
- There is no "merge two people" operation yet; a good exercise.

## Try it
Add a nickname map (`{"bob": "robert", "liz": "elizabeth"}`) applied during
normalisation. Write the tests first in `tests/unit/test_entity_resolution.py`.
