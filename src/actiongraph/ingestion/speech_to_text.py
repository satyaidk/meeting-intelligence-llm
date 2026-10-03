"""Speech-to-text with Whisper (via the ``faster-whisper`` library).

Optional: install with ``pip install -e ".[audio]"``. The first run downloads
the model weights (``base`` is ~150 MB) into the Hugging Face cache.

Why faster-whisper instead of OpenAI's original ``whisper`` package? It runs
the same model weights up to 4x faster on CPU and bundles its own audio
decoder, so Windows users do not need to install ``ffmpeg`` separately.

Known limitation: Whisper does not know *who* is speaking (no "diarization"),
so audio transcripts have no speaker names. Owners are still found when people
are addressed by name ("Sam, can you..."), but "I'll do it" cannot be
attributed. See docs/design/DESIGN.md -> Future work.
"""

from __future__ import annotations

import logging
from pathlib import Path

from actiongraph.domain.enums import SourceType
from actiongraph.errors import IngestionError
from actiongraph.ingestion.transcript import Segment, Transcript

logger = logging.getLogger(__name__)


def transcribe_media(path: Path, *, model_size: str = "base", device: str = "cpu") -> Transcript:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise IngestionError(
            'Audio/video input needs the optional dependency. Run: pip install -e ".[audio]"'
        ) from exc

    logger.info("Transcribing %s with Whisper '%s' on %s", path.name, model_size, device)
    # int8 quantisation keeps memory low and is fast on CPUs.
    model = WhisperModel(model_size, device=device, compute_type="int8")
    # vad_filter skips long silences, which also reduces hallucinated text.
    raw_segments, info = model.transcribe(str(path), vad_filter=True)

    segments = [
        Segment(text=seg.text.strip(), start=seg.start, end=seg.end)
        for seg in raw_segments  # a generator: transcription happens while iterating
        if seg.text.strip()
    ]
    if not segments:
        raise IngestionError(f"Whisper found no speech in {path.name}")

    logger.info("Transcribed %.0fs of %s audio", info.duration, info.language)
    return Transcript(
        segments=segments,
        source_type=SourceType.AUDIO,
        source_name=path.name,
        metadata={"language": info.language, "duration_seconds": f"{info.duration:.1f}"},
    )
