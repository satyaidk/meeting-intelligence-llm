"""Cross-meeting tracking helpers.

This is what makes ActionGraph more than a summariser: every meeting is read
in the context of the work that is still open from earlier meetings.

    Meeting 1  "Priya will build authentication"   -> ActionItem #1 (open)
    Meeting 2  "Authentication is blocked"         -> Event: #1 open -> blocked
    Meeting 3  "Authentication is done"            -> Event: #1 blocked -> done
"""

from __future__ import annotations

from collections.abc import Sequence

from actiongraph.domain.enums import ActionStatus, EventType, ReviewStatus
from actiongraph.enrichment.text_utils import best_match
from actiongraph.storage.models import ActionEvent, ActionItem

# Two tasks this similar (and with the same owner) are treated as the same work.
DUPLICATE_THRESHOLD = 0.75
# A risk's "blocks_task" text must be at least this similar to an action's task.
RISK_LINK_THRESHOLD = 0.5


def find_duplicate(
    task: str, owner_id: int | None, open_actions: Sequence[ActionItem]
) -> ActionItem | None:
    """Safety net for when the extractor re-creates an item that is already open."""
    same_owner = [(a.id, a.task) for a in open_actions if a.owner_id == owner_id]
    match = best_match(task, same_owner, DUPLICATE_THRESHOLD)
    if match is None:
        return None
    return next(a for a in open_actions if a.id == match[0])


def find_blocked_action(
    blocks_task: str | None, candidates: Sequence[ActionItem]
) -> ActionItem | None:
    if not blocks_task:
        return None
    match = best_match(blocks_task, [(a.id, a.task) for a in candidates], RISK_LINK_THRESHOLD)
    if match is None:
        return None
    return next(a for a in candidates if a.id == match[0])


def describe_change(from_status: str, to_status: str, new_deadline: str | None) -> EventType:
    """A deadline-only change is a postponement; anything else is a status change."""
    if from_status == to_status and new_deadline:
        return EventType.DEADLINE_CHANGED
    return EventType.STATUS_CHANGED


def apply_event(event: ActionEvent) -> None:
    """Apply a (reviewed or auto-approved) status/deadline change to its action."""
    if event.applied:
        return
    action = event.action
    if event.to_status and event.to_status != event.from_status:
        action.status = ActionStatus(event.to_status)
    if event.deadline_text:
        action.deadline_text = event.deadline_text
        action.due_date = event.due_date
    event.applied = True

    # Older proposals for this action that are still waiting for review are now
    # out of date (e.g. "postpone to Wednesday" from last week, once the item
    # is reported done). Mark them so reviewers do not act on stale information.
    for other in action.events:
        if (
            other is not event
            and not other.applied
            and other.review_status == ReviewStatus.NEEDS_REVIEW
            and _is_older(other, event)
        ):
            other.review_status = ReviewStatus.SUPERSEDED
            other.review_reasons = [*other.review_reasons, "Superseded by a later update."]


def _is_older(other: ActionEvent, event: ActionEvent) -> bool:
    if other.id is None:
        return False
    return event.id is None or other.id < event.id
