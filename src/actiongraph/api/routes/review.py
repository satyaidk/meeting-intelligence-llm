"""Review queue endpoints (human-in-the-loop)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from actiongraph.api.deps import get_session
from actiongraph.api.schemas import (
    ActionOut,
    DecisionOut,
    EventOut,
    ReviewQueueOut,
    ReviewResultOut,
    RiskOut,
)
from actiongraph.domain.enums import ItemKind
from actiongraph.services import ReviewService

router = APIRouter(prefix="/review", tags=["review"])


@router.get("", response_model=ReviewQueueOut)
def review_queue(session: Session = Depends(get_session)) -> ReviewQueueOut:
    """Everything waiting for a human decision, with the reasons it was flagged."""
    queue = ReviewService(session).queue()
    return ReviewQueueOut(
        total=sum(len(items) for items in queue.values()),
        actions=[ActionOut.model_validate(i) for i in queue[ItemKind.ACTION]],
        decisions=[DecisionOut.model_validate(i) for i in queue[ItemKind.DECISION]],
        risks=[RiskOut.model_validate(i) for i in queue[ItemKind.RISK]],
        events=[EventOut.model_validate(i) for i in queue[ItemKind.EVENT]],
    )


@router.post("/{kind}/{item_id}/approve", response_model=ReviewResultOut)
def approve(
    kind: ItemKind, item_id: int, session: Session = Depends(get_session)
) -> ReviewResultOut:
    item = ReviewService(session).approve(kind, item_id)
    return ReviewResultOut(kind=kind, id=item.id, review_status=item.review_status)


@router.post("/{kind}/{item_id}/reject", response_model=ReviewResultOut)
def reject(
    kind: ItemKind, item_id: int, session: Session = Depends(get_session)
) -> ReviewResultOut:
    item = ReviewService(session).reject(kind, item_id)
    return ReviewResultOut(kind=kind, id=item.id, review_status=item.review_status)
