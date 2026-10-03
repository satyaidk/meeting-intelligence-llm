# Sample meetings

Three meetings of one fictional team (building a mobile banking app) over
three weeks. Together they exercise every part of the pipeline, especially
**cross-meeting tracking**.

| File | Date | What it demonstrates |
|------|------|----------------------|
| `transcripts/2026-09-07_sprint-14-planning.txt` | Mon 7 Sep | New actions, owners from "X will…", "I'll…", "Sam, please…", team ownership ("We'll…"), decisions, a risk, a hedged non-commitment ("we should *maybe*…") |
| `transcripts/2026-09-14_sprint-14-sync.txt` | Mon 14 Sep | Status updates on week-1 actions (done, blocked, in progress, postponed), a blocker linked to an action, name variants (`Priya S.`, `@priya`), a deadline tied to an event ("once the credentials arrive") |
| `transcripts/2026-09-21_sprint-14-review.txt` | Mon 21 Sep | Completions, an explicit date ("October 2nd"), an ambiguous date ("next Friday"), an unresolvable date ("before the next release") |
| `other_formats/design-review.vtt` | - | WebVTT caption export with `<v Speaker>` tags (Teams/Zoom style) |

The date in each file name (`YYYY-MM-DD_title.txt`) is used as the meeting
date by `actiongraph process` and `actiongraph demo`, which matters because
deadlines like "by Friday" are resolved relative to it.

Try them:

```bash
actiongraph demo --provider offline           # all three, offline rules
actiongraph demo --provider anthropic         # all three, with Claude
actiongraph process samples/other_formats/design-review.vtt --date 2026-09-22
```
