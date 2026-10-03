"""FastAPI application factory.

``create_app()`` builds a fresh app with its own settings, database and
extractor. Using a factory (instead of a module-level ``app = FastAPI()``)
lets each test create an isolated app with a temporary database and a fake
extractor.

Run it with:  actiongraph serve      (or: uvicorn actiongraph.api.app:create_app --factory)
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from actiongraph import __version__
from actiongraph.api.routes import actions, graph, health, meetings, people, review
from actiongraph.config import Settings, get_settings
from actiongraph.errors import (
    ActionGraphError,
    ConfigurationError,
    ExtractionError,
    ExtractionRefusedError,
    IngestionError,
    InvalidOperationError,
    NotFoundError,
    UnsupportedFileTypeError,
)
from actiongraph.extraction import Extractor
from actiongraph.logging_setup import configure_logging
from actiongraph.storage import create_db_engine, init_db, make_session_factory

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

# Most specific first: the first class in an exception's MRO that appears here wins.
_STATUS_CODES: dict[type[ActionGraphError], int] = {
    NotFoundError: 404,
    UnsupportedFileTypeError: 415,
    IngestionError: 400,
    InvalidOperationError: 409,
    ExtractionRefusedError: 422,
    ExtractionError: 502,  # "bad gateway": the upstream LLM failed, not our server
    ConfigurationError: 500,
}


def create_app(settings: Settings | None = None, extractor: Extractor | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    engine = create_db_engine(settings.database_url)
    init_db(engine)

    app = FastAPI(
        title="ActionGraph API",
        version=__version__,
        description="Turn meeting transcripts into tracked decisions, actions and risks.",
    )
    app.state.settings = settings
    app.state.session_factory = make_session_factory(engine)
    app.state.extractor = extractor  # None -> built from settings on first use

    api = APIRouter(prefix="/api")
    for module in (health, meetings, actions, review, people, graph):
        api.include_router(module.router)
    app.include_router(api)

    @app.exception_handler(ActionGraphError)
    def handle_expected_error(_request: Request, exc: ActionGraphError) -> JSONResponse:
        status = next((_STATUS_CODES[c] for c in type(exc).__mro__ if c in _STATUS_CODES), 400)
        return JSONResponse(
            status_code=status, content={"detail": str(exc), "error": type(exc).__name__}
        )

    # The single-page web UI
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    return app
