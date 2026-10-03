"""Every input format becomes the same Transcript."""

from pathlib import Path

import pytest

from actiongraph.domain.enums import SourceType
from actiongraph.errors import IngestionError, UnsupportedFileTypeError
from actiongraph.ingestion import Transcript, load_transcript
from tests.conftest import SAMPLES


def test_plain_text_with_speakers() -> None:
    t = Transcript.from_text("Maya: Hello.\nSam Lee: Hi there.\ncontinued line")
    assert [s.speaker for s in t.segments] == ["Maya", "Sam Lee"]
    assert t.segments[1].text == "Hi there. continued line"
    assert t.speakers == ["Maya", "Sam Lee"]
    assert t.text == "Maya: Hello.\nSam Lee: Hi there. continued line"


def test_text_without_speakers() -> None:
    t = Transcript.from_text("We will ship on Friday.")
    assert t.segments[0].speaker is None


def test_webvtt_voice_tags(tmp_path: Path) -> None:
    t = load_transcript(SAMPLES / "other_formats" / "design-review.vtt")
    assert t.source_type is SourceType.TRANSCRIPT_FILE
    assert t.speakers == ["Maya Chen", "Jordan Patel"]
    # The two consecutive Maya cues are merged into one turn
    assert t.segments[0].text.startswith("Thanks for joining")
    assert "bottom navigation" in t.segments[0].text
    assert t.segments[0].start == 1.0


def test_srt_with_speaker_prefix(tmp_path: Path) -> None:
    srt = tmp_path / "call.srt"
    srt.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\nPriya: I'll fix the login bug.\n\n"
        "2\n00:00:03,500 --> 00:00:05,000\nSam: Thanks!\n",
        encoding="utf-8",
    )
    t = load_transcript(srt)
    assert [(s.speaker, s.text) for s in t.segments] == [
        ("Priya", "I'll fix the login bug."),
        ("Sam", "Thanks!"),
    ]


def test_json_segments(tmp_path: Path) -> None:
    path = tmp_path / "t.json"
    path.write_text('{"segments": [{"speaker": "Ana", "text": "Ship it."}]}', encoding="utf-8")
    assert load_transcript(path).text == "Ana: Ship it."


def test_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "t.json"
    path.write_text('{"segments": [{"speaker": "Ana"}]}', encoding="utf-8")
    with pytest.raises(IngestionError, match="text"):
        load_transcript(path)


def test_unsupported_extension(tmp_path: Path) -> None:
    path = tmp_path / "notes.pdf"
    path.write_bytes(b"%PDF")
    with pytest.raises(UnsupportedFileTypeError):
        load_transcript(path)


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(IngestionError, match="not found"):
        load_transcript(tmp_path / "nope.txt")


def test_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.txt"
    path.write_text("   \n", encoding="utf-8")
    with pytest.raises(IngestionError, match="No speech"):
        load_transcript(path)


def test_windows_bom_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "bom.txt"
    path.write_bytes("﻿Maya: Hello.".encode())
    assert load_transcript(path).speakers == ["Maya"]
