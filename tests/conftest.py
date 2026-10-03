"""Shared pytest fixtures and test helpers.

Fixtures defined here are available to every test file automatically.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from actiongraph.config import Settings
from actiongraph.domain.enums import ActionStatus, RiskKind, Severity
from actiongraph.domain.schemas import (
    ExtractedAction,
    ExtractedDecision,
    ExtractedRisk,
    ExtractedStatusUpdate,
    MeetingExtraction,
)
from actiongraph.extraction.base import ExtractionRequest, ExtractionResult
from actiongraph.storage import create_db_engine, init_db, make_session_factory

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLES = REPO_ROOT / "samples"
MONDAY = date(2026, 9, 7)  # meeting date used throughout the tests


# ------------------------------------------------------------------ fixtures
@pytest.fixture
def db_url(tmp_path: Path) -> str:
    """A fresh SQLite file per test - tests never share state."""
    return f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
def session(db_url: str) -> Iterator[Session]:
    engine = create_db_engine(db_url)
    init_db(engine)
    with make_session_factory(engine)() as s:
        yield s
    engine.dispose()


@pytest.fixture
def offline_settings(db_url: str) -> Settings:
    # _env_file=None: ignore the developer's personal .env during tests.
    return Settings(llm_provider="offline", database_url=db_url, _env_file=None)


# ------------------------------------------------------------------- fakes
class FakeExtractor:
    """An Extractor that returns pre-written results, in order.

    Lets us test the whole pipeline deterministically, offline, for free -
    and inspect exactly what the pipeline asked the extractor for.
    """

    name = "fake"

    def __init__(self, *extractions: MeetingExtraction) -> None:
        self._queue = list(extractions)
        self.requests: list[ExtractionRequest] = []

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        self.requests.append(request)
        return ExtractionResult(
            extraction=self._queue.pop(0), provider=self.name, model="fake-1", latency_seconds=0.0
        )


# ------------------------------------------------------------------ builders
def action(
    task: str,
    owner: str | None,
    evidence: str,
    deadline: str | None = None,
    confidence: float = 0.95,
) -> ExtractedAction:
    return ExtractedAction(
        task=task, owner=owner, deadline_text=deadline, evidence=evidence, confidence=confidence
    )


def decision(text: str, evidence: str, made_by: str | None = None) -> ExtractedDecision:
    return ExtractedDecision(decision=text, made_by=made_by, evidence=evidence, confidence=0.9)


def risk(
    description: str,
    evidence: str,
    blocks_task: str | None = None,
    kind: RiskKind = RiskKind.RISK,
) -> ExtractedRisk:
    return ExtractedRisk(
        description=description,
        kind=kind,
        severity=Severity.MEDIUM,
        blocks_task=blocks_task,
        evidence=evidence,
        confidence=0.9,
    )


def update(
    action_id: int,
    status: ActionStatus,
    evidence: str,
    deadline: str | None = None,
    confidence: float = 0.9,
) -> ExtractedStatusUpdate:
    return ExtractedStatusUpdate(
        action_id=action_id,
        new_status=status,
        new_deadline_text=deadline,
        note="Status changed.",
        evidence=evidence,
        confidence=confidence,
    )


def extraction(
    actions: list[ExtractedAction] | None = None,
    decisions: list[ExtractedDecision] | None = None,
    risks: list[ExtractedRisk] | None = None,
    updates: list[ExtractedStatusUpdate] | None = None,
    participants: list[str] | None = None,
) -> MeetingExtraction:
    return MeetingExtraction(
        summary="Test meeting.",
        participants=participants or [],
        decisions=decisions or [],
        actions=actions or [],
        risks=risks or [],
        status_updates=updates or [],
    )
