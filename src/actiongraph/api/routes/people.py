"""People endpoints: who exists, and every spelling we have seen for them."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from actiongraph.api.deps import get_session
from actiongraph.api.schemas import PersonOut
from actiongraph.storage import Repository

router = APIRouter(prefix="/people", tags=["people"])


@router.get("", response_model=list[PersonOut])
def list_people(session: Session = Depends(get_session)) -> list[PersonOut]:
    repo = Repository(session)
    open_counts: dict[int, int] = {}
    for action in repo.open_actions():
        if action.owner_id is not None:
            open_counts[action.owner_id] = open_counts.get(action.owner_id, 0) + 1
    return [
        PersonOut(
            id=p.id,
            display_name=p.display_name,
            aliases=sorted(a.alias for a in p.aliases),
            open_actions=open_counts.get(p.id, 0),
        )
        for p in repo.list_people()
    ]
