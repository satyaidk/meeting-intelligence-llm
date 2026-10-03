"""Graph endpoints: the whole ActionGraph as JSON or Mermaid text."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from actiongraph.api.deps import get_session
from actiongraph.graph import build_graph

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("")
def graph_json(session: Session = Depends(get_session)) -> dict[str, Any]:
    """Nodes and edges, ready for a graph-drawing library."""
    return build_graph(session).to_dict()


@router.get("/mermaid", response_class=PlainTextResponse)
def graph_mermaid(session: Session = Depends(get_session)) -> str:
    """Paste the result into any Markdown file on GitHub to see the diagram."""
    return build_graph(session).to_mermaid()
