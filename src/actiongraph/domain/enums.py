"""Enumerations used across the system.

``StrEnum`` members *are* strings (``ActionStatus.DONE == "done"``), so they
can be stored in plain text database columns and serialised to JSON without
any conversion code.
"""

from enum import StrEnum


class ActionStatus(StrEnum):
    """Lifecycle of an action item. See docs/architecture/DATA_MODEL.md for the state diagram."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"

    @property
    def is_closed(self) -> bool:
        return self in (ActionStatus.DONE, ActionStatus.CANCELLED)


class ReviewStatus(StrEnum):
    """Human-in-the-loop state of anything the extractor produced."""

    AUTO_APPROVED = "auto_approved"  # confident enough to trust without a human
    NEEDS_REVIEW = "needs_review"  # waiting in the review queue
    APPROVED = "approved"  # a human confirmed (or edited) it
    REJECTED = "rejected"  # a human said it is wrong; hidden from tracking
    SUPERSEDED = "superseded"  # a pending update overtaken by a newer one


class RiskKind(StrEnum):
    RISK = "risk"  # might cause trouble later
    BLOCKER = "blocker"  # is stopping work right now


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EventType(StrEnum):
    """What happened to an action item. Events form its cross-meeting timeline."""

    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    DEADLINE_CHANGED = "deadline_changed"
    MENTIONED = "mentioned"  # discussed again, nothing changed
    EDITED = "edited"  # a human changed it in the UI/CLI


class SourceType(StrEnum):
    TEXT = "text"  # pasted into the API/UI
    TRANSCRIPT_FILE = "transcript_file"  # .txt / .vtt / .srt / .json
    AUDIO = "audio"  # transcribed with Whisper


class ItemKind(StrEnum):
    """The kinds of record that can sit in the review queue."""

    ACTION = "action"
    DECISION = "decision"
    RISK = "risk"
    EVENT = "event"
