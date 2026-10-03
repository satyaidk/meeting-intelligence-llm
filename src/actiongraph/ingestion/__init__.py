"""Ingestion layer: turn any meeting input into a ``Transcript``.

    .txt / .md      -> plain "Speaker: text" lines
    .vtt / .srt     -> subtitle exports from Zoom, Teams, Google Meet
    .json           -> a list of {speaker, text, start, end} segments
    audio / video   -> speech-to-text with Whisper (optional extra)

Everything downstream only ever sees a ``Transcript``, so adding a new input
format means touching this package and nothing else.
"""

from actiongraph.ingestion.loaders import SUPPORTED_EXTENSIONS, load_transcript
from actiongraph.ingestion.transcript import Segment, Transcript

__all__ = ["SUPPORTED_EXTENSIONS", "Segment", "Transcript", "load_transcript"]
