"""Action item endpoints: the tracker."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from actiongraph.api.deps import get_session
from actiongraph.api.schemas import ActionDetailOut, ActionOut, ActionUpdate
from actiongraph.domain.enums import ActionStatus, ReviewStatus
from actiongraph.services import ReviewService
from actiongraph.storage import Repository

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("", response_model=list[ActionOut])
def list_actions(
    status: ActionStatus | None = None,
    owner_id: int | None = None,
    review_status: ReviewStatus | None = None,
    session: Session = Depends(get_session),
) -> list[ActionOut]:
    """All tracked action items (rejected ones are hidden unless you filter for them)."""
    actions = Repository(session).list_actions(
        status=status, owner_id=owner_id, review_status=review_status
    )
    return [ActionOut.model_validate(a) for a in actions]


@router.get("/{action_id}", response_model=ActionDetailOut)
def get_action(action_id: int, session: Session = Depends(get_session)) -> ActionDetailOut:
    """One action with its full cross-meeting timeline (``events``)."""
    return ActionDetailOut.model_validate(Repository(session).get_action(action_id))


@router.patch("/{action_id}", response_model=ActionDetailOut)
def update_action(
    action_id: int, body: ActionUpdate, session: Session = Depends(get_session)
) -> ActionDetailOut:
    """Human correction of an action. Counts as approval."""
    action = ReviewService(session).edit_action(
        action_id, task=body.task, owner=body.owner, deadline=body.deadline, status=body.status
    )
    return ActionDetailOut.model_validate(action)
