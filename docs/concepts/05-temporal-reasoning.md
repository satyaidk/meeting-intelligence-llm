# 05. Temporal reasoning: "by Friday" → a date

## What it is
Turning relative time expressions into absolute dates using a reference
point, here the **meeting date** (not today: "by Friday" said on Monday the
7th means the 11th, even if you process the recording a month later).

## Why it matters
Reminders, overdue lists and timelines all need real dates. And people almost
never say real dates in meetings.

## How ActionGraph does it
**Division of labour** ([ADR-0005](../adr/0005-deterministic-temporal-resolution.md)):
the LLM copies the phrase (`deadline_text: "by end of next week"`), and
`enrichment/temporal.py` computes the date.

`resolve_deadline(text, reference)` cleans the phrase (lower-case, strips
"by / before / until / the"), then tries an **ordered list of rules**. The
first rule that matches returns `(date, confidence, explanation)`:

| Phrase (meeting: Mon 7 Sep 2026) | Date | Confidence | Explanation |
|----------------------------------|------|-----------:|-------------|
| `by Friday` | Fri 11 Sep | 0.9 | first Friday after the meeting |
| `tomorrow` | Tue 8 Sep | 0.95 | meeting date + 1 day |
| `in 2 weeks` | Mon 21 Sep | 0.9 | meeting date + 2 week(s) |
| `end of next week` | Fri 18 Sep | 0.85 | Friday of next week |
| `October 2nd` | Fri 2 Oct | 0.95 | explicit calendar date |
| `next Friday` | Fri 18 Sep | **0.65** | ambiguous: read as Friday of next week |
| `next week` | Fri 18 Sep | **0.6** | read as the end of next week |
| `Monday` (said on a Monday) | Mon 14 Sep | **0.6** | assumed one week later |
| `before the next release` | **none** | 0 | depends on an unknown event |

**Order matters.** "Friday next week" must be handled by the weekday rule
before the generic "next week" rule sees it. The rule list in `temporal.py`
is commented with exactly that reasoning.

Confidence below 0.7 or no date at all → the item goes to **review** with the
explanation, so a human confirms the interpretation instead of the system
silently guessing.

## The "next Friday" problem
English speakers disagree on whether "next Friday" said on a Monday means
*this* Friday (4 days) or *next week's* Friday (11 days). There is no
universally right answer, so the correct engineering response is: pick a
documented convention, **lower the confidence**, and ask a human.

## Pitfalls
- Time zones: v0.1 works in dates only. A global team needs the meeting's time zone.
- Business calendars (holidays, sprints, fiscal quarters) are organisation-specific; "end of sprint" needs sprint data.
- Never resolve relative to `date.today()` for recorded meetings; that bug only appears when you process old recordings.

## Try it
Add support for "end of sprint" by passing an optional `sprint_end: date`
into `resolve_deadline`. Parametrised tests first.
