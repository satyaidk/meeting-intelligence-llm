"""Meeting endpoints: submit a meeting for processing and browse processed meetings.

Note: processing runs inside the request, so a call with a real LLM can take
tens of seconds. That is fine for a single user; a multi-user deployment
would hand the work to a background job queue (see docs/design/DESIGN.md).
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import asdict
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from actiongraph.api.deps import get_extractor, get_session, get_settings
from actiongraph.api.schemas import (
    MeetingCreate,
    MeetingDetailOut,
    MeetingSummaryOut,
    ProcessingReportOut,
)
from actiongraph.config import Settings
from actiongraph.errors import UnsupportedFileTypeError
from actiongraph.extraction import Extractor
from actiongraph.ingestion import SUPPORTED_EXTENSIONS, Transcript, load_transcript
from actiongraph.services import MeetingProcessor, ProcessingReport
from actiongraph.storage import Repository

router = APIRouter(prefix="/meetings", tags=["meetings"])


def _to_out(report: ProcessingReport) -> ProcessingReportOut:
    return ProcessingReportOut.model_validate(asdict(report))


@router.post("", response_model=ProcessingReportOut, status_code=201)
def create_meeting(
    body: MeetingCreate,
    session: Session = Depends(get_session),
    extractor: Extractor = Depends(get_extractor),
    settings: Settings = Depends(get_settings),
) -> ProcessingReportOut:
    """Process a pasted transcript ("Speaker: text" lines)."""
    transcript = Transcript.from_text(body.transcript)
    report = MeetingProcessor(session, extractor, settings.review_threshold).process(
        transcript, title=body.title, meeting_date=body.meeting_date
    )
    return _to_out(report)


@router.post("/upload", response_model=ProcessingReportOut, status_code=201)
def upload_meeting(
    file: UploadFile = File(..., description="Transcript (.txt/.vtt/.srt/.json) or audio/video"),
    title: str = Form(..., min_length=1, max_length=200),
    meeting_date: date = Form(...),
    session: Session = Depends(get_session),
    extractor: Extractor = Depends(get_extractor),
    settings: Settings = Depends(get_settings),
) -> ProcessingReportOut:
    """Upload a meeting file. Audio/video needs the optional `audio` extra (Whisper)."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(f"Unsupported file type '{suffix or '(none)'}'.")

    # Save to a temp folder because parsers and Whisper read from a path.
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"upload{suffix}"
        with path.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        transcript = load_transcript(
            path, whisper_model=settings.whisper_model, whisper_device=settings.whisper_device
        )
    transcript.source_name = file.filename

    report = MeetingProcessor(session, extractor, settings.review_threshold).process(
        transcript, title=title, meeting_date=meeting_date
    )
    return _to_out(report)


@router.get("", response_model=list[MeetingSummaryOut])
def list_meetings(session: Session = Depends(get_session)) -> list[MeetingSummaryOut]:
    return [MeetingSummaryOut.model_validate(m) for m in Repository(session).list_meetings()]


@router.get("/{meeting_id}", response_model=MeetingDetailOut)
def get_meeting(meeting_id: int, session: Session = Depends(get_session)) -> MeetingDetailOut:
    return MeetingDetailOut.model_validate(Repository(session).get_meeting(meeting_id))
