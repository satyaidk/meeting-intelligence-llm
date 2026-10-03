"""Read meeting files from disk and convert them to a ``Transcript``.

The public entry point is ``load_transcript(path)``; it dispatches on the file
extension to one small parser per format.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from actiongraph.domain.enums import SourceType
from actiongraph.errors import IngestionError, UnsupportedFileTypeError
from actiongraph.ingestion.transcript import Segment, Transcript, split_speaker

TEXT_EXTENSIONS = {".txt", ".md"}
SUBTITLE_EXTENSIONS = {".vtt", ".srt"}
JSON_EXTENSIONS = {".json"}
MEDIA_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".mp4", ".mov", ".mkv", ".webm"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | SUBTITLE_EXTENSIONS | JSON_EXTENSIONS | MEDIA_EXTENSIONS

# 00:01:02.500 --> 00:01:05.000   (VTT uses '.', SRT uses ',' before milliseconds)
_TIMESTAMP_LINE = re.compile(
    r"^\s*((?:\d{1,2}:)?\d{1,2}:\d{2}[.,]\d{1,3})\s*-->\s*((?:\d{1,2}:)?\d{1,2}:\d{2}[.,]\d{1,3})"
)
_VOICE_TAG = re.compile(r"<v(?:\.[\w.]+)?\s+([^>]+)>")  # WebVTT speaker tag: <v Priya Sharma>
_ANY_TAG = re.compile(r"<[^>]+>")


def load_transcript(
    path: str | Path,
    *,
    whisper_model: str = "base",
    whisper_device: str = "cpu",
) -> Transcript:
    """Load any supported meeting file and return a ``Transcript``."""
    path = Path(path)
    if not path.exists():
        raise IngestionError(f"File not found: {path}")

    suffix = path.suffix.lower()
    if suffix in MEDIA_EXTENSIONS:
        # Imported lazily: the Whisper dependency is optional and heavy.
        from actiongraph.ingestion.speech_to_text import transcribe_media

        return transcribe_media(path, model_size=whisper_model, device=whisper_device)

    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise UnsupportedFileTypeError(f"Unsupported file type '{suffix}'. Supported: {supported}")

    raw = _read_text(path)
    if suffix in SUBTITLE_EXTENSIONS:
        segments = parse_subtitles(raw)
    elif suffix in JSON_EXTENSIONS:
        segments = parse_json_segments(raw)
    else:
        segments = Transcript.from_text(raw).segments

    transcript = Transcript(
        segments=merge_consecutive_speakers(segments),
        source_type=SourceType.TRANSCRIPT_FILE,
        source_name=path.name,
    )
    if transcript.is_empty:
        raise IngestionError(f"No speech found in {path.name}")
    return transcript


def _read_text(path: Path) -> str:
    try:
        # utf-8-sig silently drops the byte-order mark that Windows editors add.
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise IngestionError(f"{path.name} is not valid UTF-8 text") from exc


def parse_subtitles(raw: str) -> list[Segment]:
    """Parse WebVTT (.vtt) or SubRip (.srt) captions.

    Both formats are blocks separated by blank lines::

        12                                  <- optional cue number (SRT always has one)
        00:01:02.500 --> 00:01:05.000       <- timing line
        <v Priya>We'll update the API</v>   <- one or more text lines
    """
    segments: list[Segment] = []
    for block in re.split(r"\n\s*\n", raw.replace("\r\n", "\n")):
        lines = [line.strip() for line in block.strip().split("\n") if line.strip()]
        start = end = None
        text_lines: list[str] = []
        for line in lines:
            timing = _TIMESTAMP_LINE.match(line)
            if timing:
                start, end = _to_seconds(timing.group(1)), _to_seconds(timing.group(2))
            elif line.isdigit() or line.startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
                continue
            elif start is not None:  # text only counts after a timing line
                text_lines.append(line)
        if not text_lines:
            continue

        joined = " ".join(text_lines)
        voice = _VOICE_TAG.search(joined)
        if voice:
            speaker: str | None = voice.group(1).strip()
            text = _ANY_TAG.sub("", joined).strip()
        else:
            speaker, text = split_speaker(_ANY_TAG.sub("", joined))
        if text:
            segments.append(Segment(text=text, speaker=speaker, start=start, end=end))
    return segments


def parse_json_segments(raw: str) -> list[Segment]:
    """Parse ``[{"speaker": ..., "text": ...}]`` or ``{"segments": [...]}``."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise IngestionError(f"Invalid JSON transcript: {exc}") from exc

    items = data.get("segments") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise IngestionError("JSON transcript must be a list of segments or {'segments': [...]}")

    segments = []
    for i, item in enumerate(items):
        if not isinstance(item, dict) or not str(item.get("text", "")).strip():
            raise IngestionError(f"Segment {i} must be an object with a non-empty 'text' field")
        segments.append(
            Segment(
                text=str(item["text"]).strip(),
                speaker=item.get("speaker"),
                start=item.get("start"),
                end=item.get("end"),
            )
        )
    return segments


def merge_consecutive_speakers(segments: list[Segment]) -> list[Segment]:
    """Join back-to-back segments from the same speaker into one turn.

    Subtitle files split speech every few seconds; merging gives the LLM
    natural speaker turns and makes the transcript shorter.
    """
    merged: list[Segment] = []
    for seg in segments:
        if merged and seg.speaker and merged[-1].speaker == seg.speaker:
            merged[-1].text = f"{merged[-1].text} {seg.text}"
            merged[-1].end = seg.end if seg.end is not None else merged[-1].end
        else:
            merged.append(Segment(text=seg.text, speaker=seg.speaker, start=seg.start, end=seg.end))
    return merged


def _to_seconds(stamp: str) -> float:
    parts = stamp.replace(",", ".").split(":")
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + float(part)
    return seconds
