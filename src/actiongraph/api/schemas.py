"""Request and response models for the HTTP API.

These are deliberately separate from the ORM tables in ``storage/models.py``:
the API is a public contract and should not change just because a database
column was renamed. ``from_attributes=True`` lets Pydantic read ORM objects.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from actiongraph.domain.enums import ActionStatus, ItemKind


class _FromORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------ requests
class MeetingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200, examples=["Sprint 14 Planning"])
    meeting_date: date = Field(examples=["2026-09-07"])
    transcript: str = Field(
        min_length=1,
        examples=[
            "Maya: Priya will handle the authentication changes.\n"
            "Sam: I'll share the research by Wednesday."
        ],
    )


class ActionUpdate(BaseModel):
    """Fields left out (null) are not changed. An empty string clears owner/deadline."""

    task: str | None = None
    owner: str | None = None
    deadline: str | None = Field(None, examples=["2026-10-02", "next Friday"])
    status: ActionStatus | None = None


# ----------------------------------------------------------------- responses
class UsageOut(BaseModel):
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


class ProcessingReportOut(BaseModel):
    meeting_id: int
    provider: str
    model: str
    latency_seconds: float
    usage: UsageOut | None
    actions_created: int
    decisions_created: int
    risks_created: int
    status_updates_applied: int
    status_updates_pending: int
    duplicates_merged: int
    items_needing_review: int
    warnings: list[str]


class PersonOut(BaseModel):
    id: int
    display_name: str
    aliases: list[str]
    open_actions: int


class ActionOut(_FromORM):
    id: int
    meeting_id: int
    task: str
    owner: str | None = Field(validation_alias="owner_name")
    owner_id: int | None
    owner_raw: str | None
    deadline_text: str | None
    due_date: date | None
    status: ActionStatus
    confidence: float
    evidence: str
    review_status: str
    review_reasons: list[str]
    created_at: datetime
    updated_at: datetime


class EventOut(_FromORM):
    id: int
    action_id: int
    action_task: str
    meeting_id: int | None
    meeting_title: str | None
    event_type: str
    from_status: str | None
    to_status: str | None
    deadline_text: str | None
    due_date: date | None
    note: str
    evidence: str
    confidence: float
    review_status: str
    review_reasons: list[str]
    applied: bool
    created_at: datetime


class DecisionOut(_FromORM):
    id: int
    meeting_id: int
    text: str
    made_by: str | None = Field(validation_alias="made_by_name")
    evidence: str
    confidence: float
    review_status: str
    review_reasons: list[str]


class RiskOut(_FromORM):
    id: int
    meeting_id: int
    description: str
    kind: str
    severity: str
    blocks_action_id: int | None
    evidence: str
    confidence: float
    review_status: str
    review_reasons: list[str]


class ActionDetailOut(ActionOut):
    events: list[EventOut]
    blocking_risks: list[RiskOut]


class MeetingSummaryOut(_FromORM):
    id: int
    title: str
    meeting_date: date
    source_type: str
    source_name: str | None
    llm_provider: str
    llm_model: str
    latency_seconds: float
    created_at: datetime


class MeetingDetailOut(MeetingSummaryOut):
    summary: str
    participants: list[str]
    transcript: str
    llm_usage: dict | None
    actions: list[ActionOut]
    decisions: list[DecisionOut]
    risks: list[RiskOut]
    status_updates: list[EventOut]


class ReviewQueueOut(BaseModel):
    total: int
    actions: list[ActionOut]
    decisions: list[DecisionOut]
    risks: list[RiskOut]
    events: list[EventOut]


class ReviewResultOut(BaseModel):
    kind: ItemKind
    id: int
    review_status: str
