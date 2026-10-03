"""Turn database rows into a graph of nodes and edges.

Node types:  meeting, action, person, decision, risk
Edge types:

    meeting  --CREATED-->   action      the action was first agreed in this meeting
    meeting  --UPDATED-->   action      a later meeting changed its status/deadline
    meeting  --DECIDED-->   decision
    meeting  --RAISED-->    risk
    action   --OWNED_BY-->  person
    decision --MADE_BY-->   person
    risk     --BLOCKS-->    action

The graph is *derived* from relational tables on request rather than stored
separately, so it can never drift out of sync with the data.

Two output formats:
* ``to_dict()``     JSON for the web UI (rendered with vis-network)
* ``to_mermaid()``  text you can paste into GitHub/Markdown to get a diagram
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from actiongraph.domain.enums import EventType, ReviewStatus
from actiongraph.storage.repository import Repository


@dataclass
class GraphNode:
    id: str  # e.g. "action:3"
    type: str
    label: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source: str
    target: str
    type: str
    label: str = ""


@dataclass
class ActionGraph:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": [asdict(n) for n in self.nodes], "edges": [asdict(e) for e in self.edges]}

    def to_mermaid(self) -> str:
        shapes = {
            "meeting": ('[["', '"]]'),
            "action": ('("', '")'),
            "person": ('(("', '"))'),
            "decision": ('{{"', '"}}'),
            "risk": ('>"', '"]'),
        }
        lines = ["flowchart LR"]
        for node in self.nodes:
            left, right = shapes[node.type]
            lines.append(f"    {_mermaid_id(node.id)}{left}{_mermaid_label(node.label)}{right}")
        for edge in self.edges:
            label = edge.label or edge.type.lower()
            source, target = _mermaid_id(edge.source), _mermaid_id(edge.target)
            lines.append(f"    {source} -->|{_mermaid_label(label)}| {target}")
        return "\n".join(lines)


def build_graph(session: Session) -> ActionGraph:
    repo = Repository(session)
    graph = ActionGraph()
    people_seen: set[int] = set()

    def add_person(person_id: int | None, name: str | None) -> str | None:
        if person_id is None:
            return None
        node_id = f"person:{person_id}"
        if person_id not in people_seen:
            people_seen.add(person_id)
            graph.nodes.append(GraphNode(node_id, "person", name or f"Person {person_id}"))
        return node_id

    for meeting in repo.list_meetings():
        graph.nodes.append(
            GraphNode(
                f"meeting:{meeting.id}",
                "meeting",
                f"{meeting.meeting_date:%d %b}: {meeting.title}",
                {"date": meeting.meeting_date.isoformat(), "summary": meeting.summary},
            )
        )

    actions = repo.list_actions()
    action_ids = {a.id for a in actions}
    for action in actions:
        node_id = f"action:{action.id}"
        graph.nodes.append(
            GraphNode(
                node_id,
                "action",
                action.task,
                {
                    "status": action.status,
                    "owner": action.owner_name,
                    "due_date": action.due_date.isoformat() if action.due_date else None,
                    "review_status": action.review_status,
                },
            )
        )
        graph.edges.append(GraphEdge(f"meeting:{action.meeting_id}", node_id, "CREATED"))
        if owner_node := add_person(action.owner_id, action.owner_name):
            graph.edges.append(GraphEdge(node_id, owner_node, "OWNED_BY"))

    for event in repo.list_events():
        is_update = event.event_type in (EventType.STATUS_CHANGED, EventType.DEADLINE_CHANGED)
        if is_update and event.applied and event.meeting_id and event.action_id in action_ids:
            label = (
                event.to_status
                if event.event_type == EventType.STATUS_CHANGED
                else f"deadline: {event.deadline_text}"
            )
            graph.edges.append(
                GraphEdge(
                    f"meeting:{event.meeting_id}", f"action:{event.action_id}", "UPDATED", label
                )
            )

    for decision in repo.list_decisions():
        node_id = f"decision:{decision.id}"
        graph.nodes.append(GraphNode(node_id, "decision", decision.text))
        graph.edges.append(GraphEdge(f"meeting:{decision.meeting_id}", node_id, "DECIDED"))
        made_by = decision.made_by.display_name if decision.made_by else None
        if person_node := add_person(decision.made_by_id, made_by):
            graph.edges.append(GraphEdge(node_id, person_node, "MADE_BY"))

    for risk in repo.list_risks():
        node_id = f"risk:{risk.id}"
        graph.nodes.append(
            GraphNode(
                node_id, "risk", risk.description, {"kind": risk.kind, "severity": risk.severity}
            )
        )
        graph.edges.append(GraphEdge(f"meeting:{risk.meeting_id}", node_id, "RAISED"))
        if risk.blocks_action_id in action_ids and risk.review_status != ReviewStatus.REJECTED:
            graph.edges.append(GraphEdge(node_id, f"action:{risk.blocks_action_id}", "BLOCKS"))

    return graph


def _mermaid_id(node_id: str) -> str:
    kind, number = node_id.split(":")
    return f"{kind[0]}{number}"  # "action:3" -> "a3"


def _mermaid_label(text: str, limit: int = 45) -> str:
    text = text.replace('"', "'").replace("|", "/").replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 3] + "..."
