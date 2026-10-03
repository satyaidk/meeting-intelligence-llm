"""Run an extractor over the golden dataset and score it.

Dataset format (one JSON file per meeting in ``evals/datasets/``)::

    {
      "id": "sprint-planning",
      "title": "Sprint 14 Planning",
      "meeting_date": "2026-09-07",
      "transcript": "../../samples/transcripts/2026-09-07_sprint-14-planning.txt",
      "open_actions": [                       # optional: context from earlier meetings
        {"id": 1, "task": "...", "owner": "Priya Sharma", "deadline": null, "status": "open"}
      ],
      "expected_actions": [{"task": "...", "owner": "Priya Sharma", "due_date": "2026-09-11"}],
      "expected_status_updates": [{"action_id": 1, "new_status": ["blocked"]}],
      "expected_decisions": ["..."],
      "expected_risks": ["..."]
    }

The transcript path is relative to the JSON file. Each case is independent:
cross-meeting behaviour is tested by giving the case its own ``open_actions``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from actiongraph.enrichment.temporal import resolve_deadline
from actiongraph.errors import ActionGraphError
from actiongraph.evaluation.metrics import (
    EvalAction,
    Scores,
    score_actions,
    score_status_updates,
    score_texts,
)
from actiongraph.extraction.base import ExtractionRequest, Extractor, OpenAction
from actiongraph.ingestion.loaders import load_transcript


@dataclass(frozen=True)
class EvalCase:
    id: str
    title: str
    meeting_date: date
    transcript_path: Path
    open_actions: list[OpenAction]
    expected_actions: list[EvalAction]
    expected_updates: dict[int, set[str]]
    expected_decisions: list[str]
    expected_risks: list[str]


def _empty() -> Scores:
    return Scores(0, 0, 0)


@dataclass
class CaseResult:
    case_id: str
    actions: Scores = field(default_factory=_empty)
    updates: Scores = field(default_factory=_empty)
    decisions: Scores = field(default_factory=_empty)
    risks: Scores = field(default_factory=_empty)
    latency_seconds: float = 0.0
    error: str | None = None


def load_cases(dataset_dir: str | Path) -> list[EvalCase]:
    cases = []
    for path in sorted(Path(dataset_dir).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        cases.append(
            EvalCase(
                id=data["id"],
                title=data["title"],
                meeting_date=date.fromisoformat(data["meeting_date"]),
                transcript_path=(path.parent / data["transcript"]).resolve(),
                open_actions=[
                    OpenAction(a["id"], a["task"], a.get("owner"), a.get("deadline"), a["status"])
                    for a in data.get("open_actions", [])
                ],
                expected_actions=[
                    EvalAction(
                        task=a["task"],
                        owner=a.get("owner"),
                        due_date=date.fromisoformat(a["due_date"]) if a.get("due_date") else None,
                    )
                    for a in data.get("expected_actions", [])
                ],
                expected_updates={
                    u["action_id"]: set(u["new_status"])
                    for u in data.get("expected_status_updates", [])
                },
                expected_decisions=data.get("expected_decisions", []),
                expected_risks=data.get("expected_risks", []),
            )
        )
    return cases


def run_case(case: EvalCase, extractor: Extractor) -> CaseResult:
    try:
        transcript = load_transcript(case.transcript_path)
        result = extractor.extract(
            ExtractionRequest(
                transcript=transcript.text,
                meeting_date=case.meeting_date,
                meeting_title=case.title,
                open_actions=case.open_actions,
            )
        )
    except ActionGraphError as exc:
        return CaseResult(case.id, error=str(exc))

    extraction = result.extraction
    predicted_actions = [
        EvalAction(
            task=a.task,
            owner=a.owner,
            due_date=resolve_deadline(a.deadline_text, case.meeting_date).due_date,
        )
        for a in extraction.actions
    ]
    predicted_updates = {u.action_id: str(u.new_status) for u in extraction.status_updates}
    return CaseResult(
        case_id=case.id,
        actions=score_actions(case.expected_actions, predicted_actions),
        updates=score_status_updates(case.expected_updates, predicted_updates),
        decisions=score_texts(case.expected_decisions, [d.decision for d in extraction.decisions]),
        risks=score_texts(case.expected_risks, [r.description for r in extraction.risks]),
        latency_seconds=result.latency_seconds,
    )


def run_eval(dataset_dir: str | Path, extractor: Extractor) -> list[CaseResult]:
    return [run_case(case, extractor) for case in load_cases(dataset_dir)]


def total(results: list[CaseResult], attribute: str) -> Scores:
    """Micro-average: add up TP/FP/FN over all cases, then compute the ratios."""
    scores = _empty()
    for result in results:
        if result.error is None:
            scores = scores + getattr(result, attribute)
    return scores
