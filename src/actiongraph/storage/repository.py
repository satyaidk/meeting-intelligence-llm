"""The Repository: every database query the application needs, in one place.

Services and API routes call ``repo.open_actions()`` instead of writing
SQLAlchemy queries inline. Benefits: queries are named after *what* they mean,
they are reused, and they can be tested on their own.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from actiongraph.domain.enums import ActionStatus, ItemKind, ReviewStatus
from actiongraph.enrichment.entity_resolution import KnownPerson
from actiongraph.errors import NotFoundError
from actiongraph.storage.models import (
    ActionEvent,
    ActionItem,
    Decision,
    Meeting,
    Person,
    PersonAlias,
    Risk,
)

CLOSED_STATUSES = (ActionStatus.DONE, ActionStatus.CANCELLED)

_MODELS = {
    ItemKind.ACTION: ActionItem,
    ItemKind.DECISION: Decision,
    ItemKind.RISK: Risk,
    ItemKind.EVENT: ActionEvent,
}


class Repository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------ meetings
    def list_meetings(self) -> Sequence[Meeting]:
        return self.session.scalars(
            select(Meeting).order_by(Meeting.meeting_date, Meeting.id)
        ).all()

    def get_meeting(self, meeting_id: int) -> Meeting:
        meeting = self.session.get(Meeting, meeting_id)
        if meeting is None:
            raise NotFoundError(f"Meeting {meeting_id} not found")
        return meeting

    # -------------------------------------------------------------- people
    def list_people(self) -> Sequence[Person]:
        return self.session.scalars(
            select(Person).options(selectinload(Person.aliases)).order_by(Person.display_name)
        ).all()

    def known_people(self) -> list[KnownPerson]:
        """People in the shape the EntityResolver understands."""
        return [
            KnownPerson(
                key=str(p.id), display_name=p.display_name, aliases={a.alias for a in p.aliases}
            )
            for p in self.list_people()
        ]

    def save_person(self, known: KnownPerson) -> Person:
        """Insert a new person or add any new aliases to an existing one."""
        if known.is_new:
            person = Person(display_name=known.display_name)
            self.session.add(person)
        else:
            person = self.session.get(Person, int(known.key))
            if person is None:
                raise NotFoundError(f"Person {known.key} not found")
            person.display_name = known.display_name
        existing = {a.alias for a in person.aliases}
        for alias in sorted(known.aliases - existing):
            person.aliases.append(PersonAlias(alias=alias))
        self.session.flush()  # assigns person.id without committing yet
        return person

    # ------------------------------------------------------------- actions
    def get_action(self, action_id: int) -> ActionItem:
        action = self.session.get(ActionItem, action_id)
        if action is None:
            raise NotFoundError(f"Action item {action_id} not found")
        return action

    def list_actions(
        self,
        *,
        status: str | None = None,
        owner_id: int | None = None,
        review_status: str | None = None,
        include_rejected: bool = False,
    ) -> Sequence[ActionItem]:
        query = select(ActionItem).options(
            selectinload(ActionItem.owner), selectinload(ActionItem.meeting)
        )
        if status:
            query = query.where(ActionItem.status == status)
        if owner_id is not None:
            query = query.where(ActionItem.owner_id == owner_id)
        if review_status:
            query = query.where(ActionItem.review_status == review_status)
        elif not include_rejected:
            query = query.where(ActionItem.review_status != ReviewStatus.REJECTED)
        return self.session.scalars(query.order_by(ActionItem.id)).all()

    def open_actions(self) -> Sequence[ActionItem]:
        """Unfinished, non-rejected actions: the context for the next meeting.

        Items still waiting for review are included on purpose - otherwise the
        next meeting would create duplicates of them.
        """
        return self.session.scalars(
            select(ActionItem)
            .options(selectinload(ActionItem.owner))
            .where(ActionItem.status.not_in(CLOSED_STATUSES))
            .where(ActionItem.review_status != ReviewStatus.REJECTED)
            .order_by(ActionItem.id)
        ).all()

    # -------------------------------------------------------------- review
    def get_item(self, kind: ItemKind, item_id: int) -> ActionItem | Decision | Risk | ActionEvent:
        item = self.session.get(_MODELS[kind], item_id)
        if item is None:
            raise NotFoundError(f"{kind.value.capitalize()} {item_id} not found")
        return item

    def pending_review(
        self, kind: ItemKind
    ) -> Sequence[ActionItem | Decision | Risk | ActionEvent]:
        model = _MODELS[kind]
        return self.session.scalars(
            select(model).where(model.review_status == ReviewStatus.NEEDS_REVIEW).order_by(model.id)
        ).all()

    def list_decisions(self) -> Sequence[Decision]:
        return self.session.scalars(
            select(Decision)
            .where(Decision.review_status != ReviewStatus.REJECTED)
            .order_by(Decision.id)
        ).all()

    def list_risks(self) -> Sequence[Risk]:
        return self.session.scalars(
            select(Risk).where(Risk.review_status != ReviewStatus.REJECTED).order_by(Risk.id)
        ).all()

    def list_events(self) -> Sequence[ActionEvent]:
        return self.session.scalars(select(ActionEvent).order_by(ActionEvent.id)).all()
