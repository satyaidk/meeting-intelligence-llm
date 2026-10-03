"""Human-in-the-loop: approve, reject, edit."""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from actiongraph.domain.enums import ActionStatus, EventType, ItemKind, ReviewStatus
from actiongraph.errors import InvalidOperationError
from actiongraph.ingestion import Transcript
from actiongraph.services import MeetingProcessor, ReviewService
from actiongraph.storage import Repository
from tests.conftest import FakeExtractor, action, extraction, update

MEETING_1 = "Maya: Sam will write the release notes.\nMaya: Sam will book the venue."
MEETING_2 = "Sam: I think the release notes are done, mostly."


@pytest.fixture
def pending_update(session: Session) -> Session:
    """Meeting 2 reports, with low confidence, that action #1 is done."""
    extractor = FakeExtractor(
        extraction(
            actions=[
                action("Write the release notes", "Sam", "Sam will write the release notes."),
                action("Book the venue", "Sam", "Sam will book the venue."),
            ]
        ),
        extraction(
            updates=[
                update(
                    1,
                    ActionStatus.DONE,
                    "I think the release notes are done, mostly.",
                    confidence=0.5,
                )
            ]
        ),
    )
    for text, day in ((MEETING_1, 7), (MEETING_2, 14)):
        MeetingProcessor(session, extractor).process(
            Transcript.from_text(text), title="m", meeting_date=date(2026, 9, day)
        )
    return session


def test_low_confidence_update_waits_in_the_queue(pending_update: Session) -> None:
    queue = ReviewService(pending_update).queue()
    assert len(queue[ItemKind.EVENT]) == 1
    assert Repository(pending_update).get_action(1).status == ActionStatus.OPEN


def test_approving_an_update_applies_it(pending_update: Session) -> None:
    service = ReviewService(pending_update)
    event = service.queue()[ItemKind.EVENT][0]

    service.approve(ItemKind.EVENT, event.id)

    assert Repository(pending_update).get_action(1).status == ActionStatus.DONE
    assert event.applied
    assert event.review_status == ReviewStatus.APPROVED
    assert service.queue()[ItemKind.EVENT] == []


def test_rejecting_an_update_leaves_the_action_alone(pending_update: Session) -> None:
    service = ReviewService(pending_update)
    event = service.queue()[ItemKind.EVENT][0]
    service.reject(ItemKind.EVENT, event.id)
    assert Repository(pending_update).get_action(1).status == ActionStatus.OPEN


def test_cannot_approve_a_stale_update(pending_update: Session) -> None:
    service = ReviewService(pending_update)
    event = service.queue()[ItemKind.EVENT][0]
    service.edit_action(1, status=ActionStatus.CANCELLED)  # someone changed it meanwhile
    with pytest.raises(InvalidOperationError, match="changed"):
        service.approve(ItemKind.EVENT, event.id)


def test_cannot_reject_an_applied_change(pending_update: Session) -> None:
    created_event = Repository(pending_update).get_action(1).events[0]
    with pytest.raises(InvalidOperationError, match="already applied"):
        ReviewService(pending_update).reject(ItemKind.EVENT, created_event.id)


def test_rejected_actions_disappear_from_tracking(pending_update: Session) -> None:
    ReviewService(pending_update).reject(ItemKind.ACTION, 2)
    repo = Repository(pending_update)
    assert [a.id for a in repo.list_actions()] == [1]
    assert [a.id for a in repo.open_actions()] == [1]


def test_edit_action(pending_update: Session) -> None:
    action_ = ReviewService(pending_update).edit_action(
        2, owner="Team", deadline="next Friday", today=date(2026, 9, 14)
    )
    assert action_.is_team_owned and action_.owner is None
    assert action_.due_date == date(2026, 9, 25)
    assert action_.review_status == ReviewStatus.APPROVED
    assert action_.events[-1].event_type == EventType.EDITED
    assert "owner, deadline" in action_.events[-1].note


def test_edit_validation(pending_update: Session) -> None:
    service = ReviewService(pending_update)
    with pytest.raises(InvalidOperationError, match="Nothing to change"):
        service.edit_action(1)
    with pytest.raises(InvalidOperationError, match="understand the deadline"):
        service.edit_action(1, deadline="whenever")
