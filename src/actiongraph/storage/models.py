"""Database tables (SQLAlchemy 2.0 ORM, typed ``Mapped[...]`` style).

Entity-relationship overview (full diagram in docs/architecture/DATA_MODEL.md)::

    Meeting 1--* ActionItem *--1 Person
    Meeting 1--* Decision
    Meeting 1--* Risk *--0..1 ActionItem      (risk BLOCKS action)
    ActionItem 1--* ActionEvent *--0..1 Meeting   (the cross-meeting timeline)
    Person 1--* PersonAlias

Enum-like columns are stored as plain strings (``"done"``), using the
``StrEnum`` values from ``domain/enums.py``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from actiongraph.domain.enums import ActionStatus, ReviewStatus


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON, list[str]: JSON}


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    meeting_date: Mapped[date] = mapped_column(Date)
    source_type: Mapped[str] = mapped_column(String(30))
    source_name: Mapped[str | None] = mapped_column(String(255))
    transcript: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")
    participants: Mapped[list[str]] = mapped_column(default=list)
    llm_provider: Mapped[str] = mapped_column(String(50))
    llm_model: Mapped[str] = mapped_column(String(100))
    llm_usage: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    latency_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    actions: Mapped[list[ActionItem]] = relationship(back_populates="meeting")
    decisions: Mapped[list[Decision]] = relationship(back_populates="meeting")
    risks: Mapped[list[Risk]] = relationship(back_populates="meeting")
    events: Mapped[list[ActionEvent]] = relationship(back_populates="meeting")

    @property
    def status_updates(self) -> list[ActionEvent]:
        """Changes this meeting made to action items from *earlier* meetings."""
        return [e for e in self.events if e.event_type in ("status_changed", "deadline_changed")]


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    aliases: Mapped[list[PersonAlias]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )
    actions: Mapped[list[ActionItem]] = relationship(back_populates="owner")


class PersonAlias(Base):
    """One normalised spelling of a person's name ("priya s", "priya sharma", ...)."""

    __tablename__ = "person_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"))
    alias: Mapped[str] = mapped_column(String(120), unique=True, index=True)

    person: Mapped[Person] = relationship(back_populates="aliases")


class ReviewableMixin:
    """Columns shared by everything that can sit in the human review queue."""

    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[str] = mapped_column(Text, default="")
    review_status: Mapped[str] = mapped_column(String(20), default=ReviewStatus.NEEDS_REVIEW)
    review_reasons: Mapped[list[str]] = mapped_column(default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ActionItem(ReviewableMixin, Base):
    __tablename__ = "action_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), index=True)
    task: Mapped[str] = mapped_column(Text)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"), index=True)
    owner_raw: Mapped[str | None] = mapped_column(String(120))  # the name as spoken
    is_team_owned: Mapped[bool] = mapped_column(default=False)
    deadline_text: Mapped[str | None] = mapped_column(String(120))
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default=ActionStatus.OPEN, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    meeting: Mapped[Meeting] = relationship(back_populates="actions")
    owner: Mapped[Person | None] = relationship(back_populates="actions")
    events: Mapped[list[ActionEvent]] = relationship(
        back_populates="action", order_by="ActionEvent.id", cascade="all, delete-orphan"
    )
    blocking_risks: Mapped[list[Risk]] = relationship(back_populates="blocks_action")

    @property
    def owner_name(self) -> str | None:
        if self.is_team_owned:
            return "Team"
        return self.owner.display_name if self.owner else None


class Decision(ReviewableMixin, Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    made_by_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    made_by_raw: Mapped[str | None] = mapped_column(String(120))

    meeting: Mapped[Meeting] = relationship(back_populates="decisions")
    made_by: Mapped[Person | None] = relationship()

    @property
    def made_by_name(self) -> str | None:
        return self.made_by.display_name if self.made_by else self.made_by_raw


class Risk(ReviewableMixin, Base):
    __tablename__ = "risks"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), index=True)
    description: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(20))
    blocks_action_id: Mapped[int | None] = mapped_column(ForeignKey("action_items.id"))

    meeting: Mapped[Meeting] = relationship(back_populates="risks")
    blocks_action: Mapped[ActionItem | None] = relationship(back_populates="blocking_risks")


class ActionEvent(ReviewableMixin, Base):
    """Something that happened to an action item, in a meeting or by a human.

    Reading an action's events in order gives its cross-meeting story:
    created (meeting 1) -> blocked (meeting 2) -> done (meeting 3).

    Status updates proposed by the extractor are stored as events *first*. If
    they are confident they are applied at once (``applied=True``); otherwise
    they wait in the review queue and are applied only when a human approves.
    """

    __tablename__ = "action_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    action_id: Mapped[int] = mapped_column(ForeignKey("action_items.id"), index=True)
    meeting_id: Mapped[int | None] = mapped_column(ForeignKey("meetings.id"))
    event_type: Mapped[str] = mapped_column(String(30))
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str | None] = mapped_column(String(20))
    deadline_text: Mapped[str | None] = mapped_column(String(120))
    due_date: Mapped[date | None] = mapped_column(Date)
    note: Mapped[str] = mapped_column(Text, default="")
    applied: Mapped[bool] = mapped_column(default=False)

    action: Mapped[ActionItem] = relationship(back_populates="events")
    meeting: Mapped[Meeting | None] = relationship(back_populates="events")

    @property
    def meeting_title(self) -> str | None:
        return self.meeting.title if self.meeting else None

    @property
    def action_task(self) -> str:
        return self.action.task
