# Brag Plan: ActionGraph

## What is this app?
ActionGraph is an LLM-powered meeting-intelligence system: it reads a meeting transcript (or audio), extracts decisions, action items, owners, deadlines and risks as schema-valid data, resolves "Priya / Priya S. / @priya" to one person and "by Friday" to a real date, tracks every action across meetings (open → blocked → done), and sends anything uncertain to a human review queue with a reason.

## The angle
Meetings don't fail in the room. They fail on Monday, when nobody remembers who promised what. The video is a calm, precise engineering film that shows ActionGraph *doing the work* on its own real sample data: the Sprint 14 meetings of the fictional mobile-banking team (Maya, Priya, Sam, Alex). The impressive part is not "AI summarises meetings". It is the division of labour: the LLM reads, plain tested code does the exact parts, a human checks the doubtful parts, and the system remembers across weeks. Every on-screen artefact is real project output (transcripts, JSON shape, resolver rules, review reasons, the action #1 timeline, test count, eval numbers).

## Hook (first 2-3 seconds)
A transcript types itself into a dark terminal-like panel: "Maya Chen: We'll update the API design by Friday." Simultaneously the headline lands: **"Every meeting ends with promises."** The voice says the same idea in different words. Then a "MON 14 SEP" stamp slams in, and the transcript lines lose focus and their speaker names, as memory fades.

## Key moments (the middle)
- The transcript turns into a structured JSON payload, object by object, then the five schema types light up as the narrator names them (decision · action · owner · deadline · risk).
- "by Friday" + "meeting: Mon 7 Sep" resolves into a **Fri 11 Sep 2026** date card; "Priya", "Priya S." and "@priya" chips arrive one by one and merge into a single **Priya Sharma** person card.
- Grounding: a real quote gets a green "found in transcript · 100%" tick; an invented one gets a red "not found". Then a real review-queue card ("Deadline 'next Friday' was read as Fri 02 Oct 2026; please confirm.") gets approved by a simulated cursor click.
- Action #1's real timeline across three meetings: OPEN (7 Sep) → BLOCKED (14 Sep) → DONE (21 Sep).
- Proof: 1 model call per meeting, 160 tests, and the honest eval stat (regex baseline F1 0.96 on tuned data → 0.00 on held-out speech).

## Outro / punchline
The wordmark **ActionGraph**, tagline "Meetings → tracked work.", stack line "Python · Claude · FastAPI · SQLite". Narration: "Action Graph. Leave every meeting with the work already tracked." Logo holds; music swells after the voice ends.

## User flow worth showing
1. **Entry:** a meeting transcript (`samples/transcripts/2026-09-07_sprint-14-planning.txt`).
2. **Key action:** one structured-output extraction → deterministic enrichment (dates, people, grounding) → review queue approve.
3. **Result:** a tracked action whose timeline updates across three meetings (`actiongraph timeline 1`).

## Tone
- Preset: `polished`
- Creative direction: "precise engineering launch film: calm confidence, the product doing the work, real artefacts only"
- Interpretation: restrained typography and soft blur transitions, longer holds than a typical brag, no jokes forced. The user requested 60 seconds with narration, so the polished 3-4 scene shape is extended to 8 narrated beats, each one idea. Narration carries the story; visuals show the real thing the voice describes.

## Format: landscape — 1920x1080
## Duration: 60s (user requested `--length 60s`; overrides the 15-25s default)

## Visual identity (from the project)
Source: `src/actiongraph/web/styles.css` (dark-theme tokens) and the graph palette in `web/app.js`.
- Background: `#12151c` (surface `#1b1f29`, border `#2c3240`)
- Accent: `#748ffc`
- Text: `#e6e8ee` (muted `#9aa3b5`)
- Status / graph colours: done/action `#40c057`, blocked/risk `#fa5252`, review/person `#fab005`, decision `#be4bdb`, meeting `#5c7cfa`
- Display font: the UI uses `system-ui`; for video, **Montserrat** (900 / 400) for statements
- Data font: **JetBrains Mono** for transcripts, JSON, labels and numbers (human speech vs machine structure)
- Strongest visual element: the action timeline (created → blocked → done) and the review card with its plain-English reason

## Share copy (draft)
Built ActionGraph: it turns meeting transcripts into tracked decisions, owners and deadlines, verifies every item against the transcript, and follows each action from "open" to "done" across meetings.

## Voiceover script
Voice: Kokoro `af_heart` (female, en-US), via `npx hyperframes tts`. One clip per scene, merged into `composition/assets/voiceover.wav` at the offsets below.

| Scene | Starts at | Clip length | Line |
|-------|-----------|------------:|------|
| 1 | 0.6s | 7.34s | Every meeting ends with promises. 'I'll handle it.' 'By Friday.' Then Monday comes, and nobody remembers who said what. |
| 2 | 8.6s | 4.18s | Action Graph turns that conversation into work you can actually track. |
| 3 | 13.4s | 7.47s | Claude reads the transcript and returns structured, validated data: every decision, action, owner, deadline, and risk. |
| 4 | 21.8s | 9.22s | Then plain, tested code handles what has to be exact. 'By Friday' becomes a real date. Priya, Priya S., and at Priya become one person. |
| 5 | 31.8s | 6.70s | Every item has to quote the transcript. And anything the system isn't sure about goes to a human, with the reason why. |
| 6 | 39.4s | 6.49s | And it remembers. Week one, Priya takes on authentication. Week two, it's blocked. Week three, it's done. |
| 7 | 46.8s | 5.40s | One model call per meeting. A hundred and sixty tests. And an honest eval to back it up. |
| 8 | 53.2s | 3.50s | Action Graph. Leave every meeting with the work already tracked. |

138 words over 60s (2.3 words/s): room to breathe.

## Audio direction
- Role: warm bed under narration, sparse professional accents
- Music: `happy-beats-business-moves-vol-12-by-ende-dot-app.mp3` ("steady and clean"; polished/cinematic)
- Music treatment: fade in over 0.5s; sit low under the voice (voice carve, roughly 0.12-0.15 equivalent); swell back up after the last line (~56.8s); fade out over the last 1.2s
- Music cue guidance: bundled preset `<skill-dir>/assets/music/cues/happy-beats-business-moves-vol-12-by-ende-dot-app.music-cues.json` (109.96 BPM). Strong-cue locks: **8.74s** wordmark reveal, **44.74s** "DONE" status, **48.55s** "160" stat. Beat grid ~0.545s; sequential text holds at least one beat pair.
- Audio-reactive treatment: subtle; music bass makes the accent background glow breathe and RMS lifts the graph-grid presence. No waveform/equalizer visuals.
- SFX posture: sparse (polished), motion-matched, low-HF-risk files, quiet under narration
- Audio-coupled moments: transcript typing (a few soft key ticks), date stamp, wordmark, JSON objects landing, date resolve, name merge, grounding tick, approve click, status pills, stats, final logo
- Restraint rule: never cover a spoken word with a loud cue; no stacked SFX; nothing louder than the voice.

## Storyboard

### Scene 1 — Promises — 0.0–8.1s
Left: a dark transcript panel; three real lines from the planning meeting type on. Right: headline "Every meeting ends with promises." "will handle" and "by Friday" highlight as the voice says them. At ~4.9s a "MON 14 SEP" stamp lands; at ~6.1s the transcript defocuses and speaker names become "???".
Sequential/interaction: yes, the lines type on one after another; the highlights follow the voice.
Audio intent: quiet opening, voice-led.
Audio-coupled idea: sparse key ticks on typing; a soft thud on the date stamp.
Music: fade in, low.
Transition mood: soft (focus pull: memory fades) → Scene 2

### Scene 2 — Reveal — 8.1–12.95s
Wordmark "ActionGraph" with a small node-edge mark, locked to the 8.74s strong cue. Tagline "Meetings → tracked work."
Sequential/interaction: graph mark edges draw in.
Audio intent: confident arrival.
Audio-coupled idea: one warm reveal hit on the wordmark.
Transition mood: soft (blur crossfade) → Scene 3

### Scene 3 — Extraction — 12.95–21.2s
Split frame: the transcript (left) → "1 call · structured output" → JSON (right) assembling three action objects one by one (task / owner / deadline_text, real values). Then five schema chips light up in sequence as spoken: DECISION · ACTION · OWNER · DEADLINE · RISK.
Sequential/interaction: yes, 3 JSON objects arrive one by one (held, not removed); 5 chips light in order and stay.
Audio intent: steady build.
Audio-coupled idea: soft drop on each JSON object.
Transition mood: clean (push slide) → Scene 4

### Scene 4 — Exact parts — 21.2–31.2s
Headline "Code does the exact parts." Two panels. TEMPORAL: "by Friday" + "meeting: Mon 7 Sep" → **Fri 11 Sep 2026**, rule "first Friday after the meeting · 0.90". ENTITY: chips "Priya", "Priya S.", "@priya" arrive as spoken, then merge into the **Priya Sharma** person card.
Sequential/interaction: yes, the date resolves on "becomes a real date"; the name chips arrive one by one and merge.
Audio intent: precise, mechanical.
Audio-coupled idea: a click as the date locks; a soft thud on the merge.
Transition mood: soft (blur crossfade) → Scene 5

### Scene 5 — Trust — 31.2–38.9s
Left: grounding checks. Real quote "Priya will handle the authentication changes." ✓ found · 100%; invented quote "Priya agreed to rewrite the billing service by Monday." ✗ not found. Right: real review card (NEEDS REVIEW; "Draft the beta announcement email"; Sam Lee; reason "Deadline 'next Friday' was read as Fri 02 Oct 2026; please confirm."). The reason highlights on "with the reason why"; a cursor clicks Approve → APPROVED.
Sequential/interaction: yes, two checks in order; simulated cursor click.
Audio intent: careful, trustworthy.
Audio-coupled idea: tick on found, muted buzz on not found, mouse click on approve.
Transition mood: clean (push slide) → Scene 6

### Scene 6 — Memory — 38.9–46.3s
Card "#1 Handle the authentication changes · Priya Sharma". A three-meeting timeline draws left to right: 07 SEP Sprint 14 Planning → OPEN, 14 SEP Sprint 14 Sync → BLOCKED (blocker chip "waiting on security review"), 21 SEP Sprint 14 Review → DONE (locked to the 44.74s strong cue). Real evidence quotes under each node.
Sequential/interaction: yes, three status nodes on "week one / two / three".
Audio intent: payoff.
Audio-coupled idea: soft drop on OPEN, low thud on BLOCKED, bell on DONE.
Transition mood: soft (blur crossfade) → Scene 7

### Scene 7 — Proof — 46.3–52.6s
Three stat columns in mono numerals: **1** "model call per meeting"; **160** "tests passing" (counts up, locked to 48.55s); **0.96 → 0.00** "baseline F1: tuned vs held-out". Small footer "pytest · ruff · GitHub Actions".
Sequential/interaction: yes, three stats one by one as spoken; all held.
Audio intent: quiet confidence.
Audio-coupled idea: soft drop per stat.
Transition mood: soft (focus pull) → Scene 8

### Scene 8 — Outro — 52.6–60.0s
Wordmark + graph mark, tagline "Meetings → tracked work.", stack line "Python · Claude · FastAPI · SQLite". Holds to the end, no fade to black.
Sequential/interaction: none.
Audio intent: resolve; music swells after the voice.
Audio-coupled idea: a bell on the wordmark landing.

**Music mood for this video:** polished, steady
**Audio summary:** a low, steady bed under a calm female narrator, a handful of soft motion-matched accents, one bell for "done" and one for the logo, and a music swell to close.

No secrets or personal data appear: all names are the fictional sample team from `samples/`.
