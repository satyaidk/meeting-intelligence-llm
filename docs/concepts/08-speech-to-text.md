# 08. Speech-to-text with Whisper

## What it is
**Automatic speech recognition (ASR)** converts audio into text. Whisper is
an open-weights ASR model released by OpenAI; `faster-whisper` is a
re-implementation that runs the same weights faster on ordinary CPUs.

## How ActionGraph uses it (`ingestion/speech_to_text.py`)
```python
model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe("meeting.m4a", vad_filter=True)
```

| Setting | Meaning |
|---------|---------|
| model size (`tiny` → `large-v3`) | Bigger = more accurate and slower. `base` is a good laptop default (`ACTIONGRAPH_WHISPER_MODEL`) |
| `compute_type="int8"` | *Quantisation*: smaller numbers, less memory, faster on CPU, tiny accuracy cost |
| `vad_filter=True` | *Voice activity detection*: skips silence, which is faster and reduces "hallucinated" text in silent stretches |

Install with `pip install -e ".[audio]"`. The first run downloads the model
weights (~150 MB for `base`). Audio never leaves your machine.

## The diarization gap
Whisper outputs *what* was said, not *who* said it. Without speaker names:
- "Sam, can you share the research?" still gives owner = Sam (named in the text);
- "I'll do it" cannot be attributed, so the owner is unknown, and the item goes to review.

Adding **speaker diarization** (e.g. `pyannote.audio`) and aligning its
speaker turns with Whisper's timestamps is the top roadmap item.

## Pitfalls
- Recognition errors on names ("Priya" → "Korea") break entity resolution; fuzzy matching and review catch some of them.
- Long recordings take minutes on CPU, too long for a synchronous HTTP request in production (see the design doc's future work: background jobs).
- Language detection is automatic; mixed-language meetings may need an explicit `language=` argument.

## Try it
Record a 30-second voice memo with one clear commitment ("Alex, please send
the slides by Thursday"), then:

```powershell
pip install -e ".[audio]"
actiongraph process memo.m4a --date 2026-10-05 --provider anthropic
```
