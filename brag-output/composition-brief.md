# Hyperframes Composition Brief: ActionGraph

## Objective
Create a 60-second narrated launch-style brag video for ActionGraph, an LLM meeting-intelligence system.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080, 30 fps
- Duration: 60 seconds (user request; overrides the 15-25s default)

## Source Material
- Project root: `C:\Users\nikad\Desktop\LLM Project`
- Primary files read: `README.md`, `src/actiongraph/web/index.html`, `web/styles.css`, `web/app.js`, `samples/transcripts/*.txt`, `src/actiongraph/domain/schemas.py`, `enrichment/temporal.py`, `enrichment/entity_resolution.py`, `enrichment/confidence.py`, `tests/unit/test_grounding.py`, `evals/`, demo CLI output (`actiongraph demo`, `actiongraph timeline 1`, `actiongraph review`)
- Product name: ActionGraph
- Tagline / strongest claim: "Meetings → tracked work." / "turns conversations into trackable, reviewable work"
- Key UI or visual moment to recreate: the action timeline (created → blocked → done) and the review-queue card with its reason
- Copy that must appear verbatim:
  - "Maya Chen: We'll update the API design by Friday."
  - "Maya Chen: Priya will handle the authentication changes."
  - "Maya Chen: Sam, please share the user research by Wednesday."
  - "Deadline 'next Friday' was read as Fri 02 Oct 2026; please confirm."
  - "The authentication changes are blocked." / "Authentication is completed."

## Creative Direction
- Tone preset: polished
- Creative direction: precise engineering launch film: calm confidence, the product doing the work, real artefacts only
- Interpretation: restrained type, blur/focus transitions with two push-slide accents, generous holds, narration-led pacing
- Angle: meetings fail on Monday, not in the room. Show the division of labour: LLM reads → code makes it exact → humans check the doubtful parts → the system remembers across weeks.
- Hook: transcript typing + "Every meeting ends with promises." then the Monday stamp and fading memory
- Outro / punchline: "ActionGraph — Meetings → tracked work."; narrator: "Leave every meeting with the work already tracked."
- Avoid:
  - Generic SaaS language
  - Abstract filler visuals
  - Unrelated visual redesign (stay in the product's dark palette)

## Visual Identity
- Background: `#12151c` (surface `#1b1f29`, border `#2c3240`)
- Text: `#e6e8ee` (muted `#9aa3b5`)
- Accent: `#748ffc`
- Status: done `#40c057`, blocked/risk `#fa5252`, review/person `#fab005`, decision `#be4bdb`, meeting `#5c7cfa`
- Display font: Montserrat 900/400 (bundled); the product UI uses system-ui
- Data font: JetBrains Mono 400/700 (bundled)
- Visual references from the project: transcript lines, MeetingExtraction JSON, status pills, review card + reasons, timeline dots, graph node colours

## Storyboard
Use the storyboard in `brag-output/brag-plan.md` as the creative contract.

Scene summary:
1. Promises — 0.0–8.1s — transcript types; "Every meeting ends with promises."; MON 14 SEP stamp; memory fades
2. Reveal — 8.1–12.95s — ActionGraph wordmark (beat-locked 8.74s), "Meetings → tracked work."
3. Extraction — 12.95–21.2s — transcript → JSON objects; five schema chips light in order
4. Exact parts — 21.2–31.2s — "by Friday" → Fri 11 Sep 2026; Priya / Priya S. / @priya → Priya Sharma
5. Trust — 31.2–38.9s — grounding ✓/✗; review card reason; cursor approves
6. Memory — 38.9–46.3s — action #1: OPEN → BLOCKED → DONE (DONE beat-locked 44.74s)
7. Proof — 46.3–52.6s — 1 call · 160 tests (beat-locked 48.55s) · 0.96 → 0.00 F1
8. Outro — 52.6–60.0s — wordmark, tagline, stack line; hold

## Audio
- Audio role: warm bed under narration + sparse accents
- Audio arc: fade in → low under the voice → swell after the final line → fade out
- Music: `assets/music/happy-beats-business-moves-vol-12-by-ende-dot-app.mp3`
- Music treatment: carve the bed around the voice (hyperframes-audio voiceover carve); fade-in 0.5s, swell from 56.9s, fade out over the final 1.2s
- Music cue guidance: bundled preset (109.96 BPM); locks at 8.74s, 44.74s, 48.55s
- Audio-reactive treatment: subtle; bass → background glow scale/opacity, RMS → grid presence (pre-extracted to `assets/audio-data.js`)
- Voiceover: `assets/voiceover.wav` (Kokoro `af_heart`, merged at the scene offsets in the plan), its own track, volume 1
- Audio-coupled moments: see plan per scene
- SFX selection guidance: low-HF-risk picks from `sfx-analysis.md`; soft impacts, drops, clicks; one bell for DONE and one for the logo
- Exact SFX choice: chosen after the animation exists
- Audio files: copied into `brag-output/composition/assets/`

## Hyperframes Instructions
Follow `hyperframes-core`, `hyperframes-animation`, `hyperframes-creative`, `hyperframes-keyframes`, `hyperframes-cli`. Single monolithic `index.html`, one paused GSAP timeline keyed `main`. Show real UI/copy, keep all text readable (hold ≥ reading floor), honour the music treatment, run `npx hyperframes check` before render.
