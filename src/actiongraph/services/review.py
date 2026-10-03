"""Human-in-the-loop operations: approve, reject and edit.

The review queue holds everything the pipeline was not sure about (see
``enrichment/confidence.py`` for the rules). A reviewer can:

* **approve** - the item is right. For a pending status update, this is the
  moment the change is actually applied to the action item.
* **reject**  - the item is wrong. Rejected actions disappear from tracking
  (but stay in the database for auditing and evaluation).
* **edit**    - fix an action's task/owner/deadline/status. Editing counts as
  approval, and the change is recorded as an ``edited`` event.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from actiongraph.domain.enums import ActionStatus, EventType, ItemKind, ReviewStatus
from actiongraph.enrichment.entity_resolution import EntityResolver, ResolutionMethod
from actiongraph.enrichment.temporal import resolve_deadline
from actiongraph.errors import InvalidOperationError
from actiongraph.services.tracking import apply_event
from actiongraph.storage.models import ActionEvent, ActionItem, Decision, Risk
from actiongraph.storage.repository import Repository

Reviewable = ActionItem | Decision | Risk | ActionEvent


class ReviewService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = Repository(session)

    def queue(self) -> dict[ItemKind, list[Reviewable]]:
        return {kind: list(self.repo.pending_review(kind)) for kind in ItemKind}

    def approve(self, kind: ItemKind, item_id: int) -> Reviewable:
        item = self.repo.get_item(kind, item_id)
        if isinstance(item, ActionEvent):
            if item.action.status != item.from_status and item.to_status != item.from_status:
                raise InvalidOperationError(
                    f"Action {item.action_id} changed to '{item.action.status}' after this update "
                    "was proposed; reject it or edit the action directly."
                )
            apply_event(item)
        item.review_status = ReviewStatus.APPROVED
        self.session.commit()
        return item

    def reject(self, kind: ItemKind, item_id: int) -> Reviewable:
        item = self.repo.get_item(kind, item_id)
        if isinstance(item, ActionEvent) and item.applied:
            raise InvalidOperationError(
                "This change was already applied. Edit the action item to change it back."
            )
        item.review_status = ReviewStatus.REJECTED
        self.session.commit()
        return item

    def edit_action(
        self,
        action_id: int,
        *,
        task: str | None = None,
        owner: str | None = None,
        deadline: str | None = None,
        status: ActionStatus | None = None,
        today: date | None = None,
    ) -> ActionItem:
        """Apply a human correction. ``None`` means "leave unchanged"; ``""`` clears owner/deadline.

        Deadlines typed by a person are relative to *today* (not the meeting date).
        """
        action = self.repo.get_action(action_id)
        changes: list[str] = []
        from_status = action.status

        if task is not None and task.strip() and task.strip() != action.task:
            action.task = task.strip()
            changes.append("task")

        if owner is not None:
            self._set_owner(action, owner)
            changes.append("owner")

        if deadline is not None:
            if not deadline.strip():
                action.deadline_text, action.due_date = None, None
            else:
                resolved = resolve_deadline(deadline, today or date.today())
                if not resolved.is_resolved:
                    raise InvalidOperationError(
                        f"Could not understand the deadline '{deadline}'. Try YYYY-MM-DD."
                    )
                action.deadline_text, action.due_date = deadline.strip(), resolved.due_date
            changes.append("deadline")

        if status is not None and status != action.status:
            action.status = status
            changes.append("status")

        if not changes:
            raise InvalidOperationError("Nothing to change.")

        action.events.append(
            ActionEvent(
                event_type=EventType.EDITED,
                from_status=from_status,
                to_status=action.status,
                deadline_text=action.deadline_text,
                due_date=action.due_date,
                note=f"Edited by a reviewer: {', '.join(changes)}.",
                confidence=1.0,
                review_status=ReviewStatus.APPROVED,
                applied=True,
            )
        )
        action.review_status = ReviewStatus.APPROVED
        action.review_reasons = []
        self.session.commit()
        return action

    def _set_owner(self, action: ActionItem, owner: str) -> None:
        action.owner_raw = owner.strip() or None
        resolution = EntityResolver(self.repo.known_people()).resolve(owner)
        if resolution.method is ResolutionMethod.AMBIGUOUS:
            raise InvalidOperationError(
                f"'{owner}' is ambiguous ({', '.join(resolution.candidates)}). Use the full name."
            )
        action.is_team_owned = resolution.is_team
        action.owner = self.repo.save_person(resolution.person) if resolution.person else None
