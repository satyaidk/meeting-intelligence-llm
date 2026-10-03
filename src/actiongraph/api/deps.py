"""FastAPI dependencies ("dependency injection").

A route declares what it needs - ``session: Session = Depends(get_session)`` -
and FastAPI calls these functions to provide it. Tests can swap any of them
(e.g. a fake extractor) without touching route code.
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from actiongraph.config import Settings
from actiongraph.extraction import Extractor, build_extractor


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_session(request: Request) -> Iterator[Session]:
    """One database session per HTTP request, always closed afterwards."""
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_extractor(request: Request) -> Extractor:
    # Built lazily so the server can start (and serve the UI) without an API key.
    if request.app.state.extractor is None:
        request.app.state.extractor = build_extractor(request.app.state.settings)
    return request.app.state.extractor
