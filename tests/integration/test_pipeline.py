"""End-to-end pipeline over three meetings, with a scripted (fake) extractor.

The fake extractor returns hand-written extractions, so these tests check
everything AFTER the LLM: grounding, entity resolution, deadlines, review
routing, cross-meeting status updates, de-duplication, risk linking and the
database transaction.
"""

from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from actiongraph.domain.enums import ActionStatus, EventType, ReviewStatus, RiskKind
from actiongraph.errors import ExtractionError
from actiongraph.extraction.base import ExtractionRequest, ExtractionResult
from actiongraph.graph import build_graph
from actiongraph.ingestion import Transcript
from actiongraph.services import MeetingProcessor
from actiongraph.storage import Repository
from actiongraph.storage.models import ActionItem, Meeting, Person, Risk
from tests.conftest import FakeExtractor, action, decision, extraction, risk, update

MEETING_1 = """\
Maya Chen: Priya will handle the authentication changes.
Maya Chen: We'll update the API design by Friday.
Maya Chen: Sam, please share the user research by Wednesday.
Priya Sharma: We should maybe look at biometric login.
Alex Kim: One concern: the staging environment still runs the old database.
Maya Chen: We decided to use OAuth 2.0 for the mobile app."""

EXTRACTION_1 = extraction(
    participants=["Maya Chen", "Priya Sharma", "Alex Kim"],
    actions=[
        action(
            "Implement the authentication changes",
            "Priya",
            "Priya will handle the authentication changes.",
        ),
        action(
            "Update the API design", "Team", "We'll update the API design by Friday.", "by Friday"
        ),
        action(
            "Share the user research",
            "Sam",
            "Sam, please share the user research by Wednesday.",
            "by Wednesday",
        ),
        action(
            "Look at biometric login",
            "Team",
            "We should maybe look at biometric login.",
            confidence=0.4,
        ),
    ],
    decisions=[
        decision(
            "Use OAuth 2.0 for the mobile app",
            "We decided to use OAuth 2.0 for the mobile app.",
            "Maya Chen",
        )
    ],
    risks=[
        risk(
            "Staging runs an old database",
            "One concern: the staging environment still runs the old database.",
        )
    ],
)

MEETING_2 = """\
Priya S.: The authentication changes are blocked by the security review.
Sam Lee: Can we push the user research to next Wednesday?
Maya Chen: @priya, please also pair with Alex on the staging config.
Maya Chen: And Priya will keep working on the authentication changes."""

EXTRACTION_2 = extraction(
    updates=[
        update(
            1,
            ActionStatus.BLOCKED,
            "The authentication changes are blocked by the security review.",
        ),
        update(
            3,
            ActionStatus.OPEN,
            "Can we push the user research to next Wednesday?",
            deadline="next Wednesday",
        ),
        update(999, ActionStatus.DONE, "Something nobody said."),
    ],
    actions=[
        action(
            "Pair with Alex on the staging config",
            "@priya",
            "@priya, please also pair with Alex on the staging config.",
        ),
        # The model re-created an item that is already open (#1): must be merged.
        action(
            "Implement the authentication changes",
            "Priya S.",
            "And Priya will keep working on the authentication changes.",
        ),
    ],
    risks=[
        risk(
            "Security review blocks authentication",
            "The authentication changes are blocked by the security review.",
            blocks_task="authentication changes",
            kind=RiskKind.BLOCKER,
        )
    ],
)

MEETING_3 = """\
Priya Sharma: Authentication is completed and merged.
Sam Lee: I shared the user research yesterday."""

EXTRACTION_3 = extraction(
    updates=[
        update(1, ActionStatus.DONE, "Authentication is completed and merged."),
        update(3, ActionStatus.DONE, "I shared the user research yesterday."),
    ]
)


def _process(session: Session, extractor: FakeExtractor, text: str, day: int):
    return MeetingProcessor(session, extractor).process(
        Transcript.from_text(text), title=f"Meeting on the {day}th", meeting_date=date(2026, 9, day)
    )


@pytest.fixture
def three_meetings(session: Session) -> tuple[Session, FakeExtractor, list]:
    extractor = FakeExtractor(EXTRACTION_1, EXTRACTION_2, EXTRACTION_3)
    reports = [
        _process(session, extractor, MEETING_1, 7),
        _process(session, extractor, MEETING_2, 14),
        _process(session, extractor, MEETING_3, 21),
    ]
    return session, extractor, reports


# ------------------------------------------------------------- meeting 1
def test_first_meeting_creates_resolved_actions(session: Session) -> None:
    report = _process(session, FakeExtractor(EXTRACTION_1), MEETING_1, 7)

    assert (report.actions_created, report.decisions_created, report.risks_created) == (4, 1, 1)
    auth, api, research, biometric = Repository(session).list_actions()

    assert auth.owner_name == "Priya Sharma"  # "Priya" resolved to the speaker's full name
    assert api.is_team_owned
    assert api.due_date == date(2026, 9, 11)  # "by Friday" after Monday the 7th
    assert research.owner_name == "Sam"
    assert research.due_date == date(2026, 9, 9)
    assert auth.review_status == ReviewStatus.AUTO_APPROVED
    assert biometric.review_status == ReviewStatus.NEEDS_REVIEW
    assert report.items_needing_review == 1
    assert [e.event_type for e in auth.events] == [EventType.CREATED]


# ------------------------------------------------------------- meeting 2
def test_open_actions_are_sent_as_context(three_meetings) -> None:
    _, extractor, _ = three_meetings
    first, second, _ = extractor.requests
    assert first.open_actions == []
    assert [a.id for a in second.open_actions] == [1, 2, 3, 4]  # pending review included
    assert "Priya Sharma" in second.known_people


def test_status_updates_duplicates_and_hallucinated_ids(session: Session) -> None:
    extractor = FakeExtractor(EXTRACTION_1, EXTRACTION_2)
    _process(session, extractor, MEETING_1, 7)
    report = _process(session, extractor, MEETING_2, 14)

    auth = Repository(session).get_action(1)
    assert auth.status == ActionStatus.BLOCKED
    # Events follow pipeline stage order: new actions (stage 5) before status updates (stage 7)
    assert [e.event_type for e in auth.events] == [
        EventType.CREATED,
        EventType.MENTIONED,  # the duplicate was folded into the existing item
        EventType.STATUS_CHANGED,
    ]
    assert report.duplicates_merged == 1
    assert report.status_updates_applied == 1
    assert any("unknown action id 999" in w for w in report.warnings)

    # "next Wednesday" is ambiguous -> the postponement waits for a human
    research = Repository(session).get_action(3)
    pending = research.events[-1]
    assert pending.event_type == EventType.DEADLINE_CHANGED
    assert not pending.applied
    assert pending.review_status == ReviewStatus.NEEDS_REVIEW
    assert research.deadline_text == "by Wednesday"  # unchanged until approved
    assert report.status_updates_pending == 1


def test_name_variants_merge_into_one_person(three_meetings) -> None:
    session, _, _ = three_meetings
    priya_ids = {
        a.owner_id
        for a in Repository(session).list_actions()
        if a.owner_raw and "riya" in a.owner_raw
    }
    assert len(priya_ids) == 1
    priya = session.get(Person, priya_ids.pop())
    assert {"priya", "priya s", "priya sharma"} <= {a.alias for a in priya.aliases}


def test_blocker_is_linked_to_the_action_it_blocks(three_meetings) -> None:
    session, _, _ = three_meetings
    blocker = session.scalars(select(Risk).where(Risk.kind == RiskKind.BLOCKER)).one()
    assert blocker.blocks_action_id == 1


# ------------------------------------------------------------- meeting 3
def test_story_across_three_meetings(three_meetings) -> None:
    session, _, _ = three_meetings
    auth = Repository(session).get_action(1)
    statuses = [
        (e.from_status, e.to_status) for e in auth.events if e.event_type == "status_changed"
    ]
    assert statuses == [("open", "blocked"), ("blocked", "done")]
    assert auth.status == ActionStatus.DONE


def test_newer_update_supersedes_stale_pending_one(three_meetings) -> None:
    session, _, _ = three_meetings
    research = Repository(session).get_action(3)
    assert research.status == ActionStatus.DONE
    stale = next(e for e in research.events if e.event_type == EventType.DEADLINE_CHANGED)
    assert stale.review_status == ReviewStatus.SUPERSEDED


def test_closed_actions_are_no_longer_context(three_meetings) -> None:
    session, _, _ = three_meetings
    open_ids = [a.id for a in Repository(session).open_actions()]
    assert 1 not in open_ids and 3 not in open_ids
    assert 5 in open_ids  # "Pair with Alex" from meeting 2 is still open


def test_graph_reflects_the_story(three_meetings) -> None:
    session, _, _ = three_meetings
    graph = build_graph(session)
    edges = {(e.source, e.type, e.target) for e in graph.edges}

    assert ("meeting:1", "CREATED", "action:1") in edges
    assert ("meeting:2", "UPDATED", "action:1") in edges
    assert ("meeting:3", "UPDATED", "action:1") in edges
    assert any(e.type == "BLOCKS" and e.target == "action:1" for e in graph.edges)
    assert graph.to_mermaid().startswith("flowchart LR")


# ----------------------------------------------------------- transactions
class FailingExtractor:
    name = "failing"

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        raise ExtractionError("LLM unavailable")


def test_failed_extraction_leaves_database_untouched(session: Session) -> None:
    with pytest.raises(ExtractionError):
        MeetingProcessor(session, FailingExtractor()).process(
            Transcript.from_text(MEETING_1), title="x", meeting_date=date(2026, 9, 7)
        )
    assert session.scalar(select(func.count()).select_from(Meeting)) == 0
    assert session.scalar(select(func.count()).select_from(ActionItem)) == 0
