"""The offline baseline extractor, run on the sample meetings."""

from datetime import date

from actiongraph.domain.enums import ActionStatus
from actiongraph.extraction.base import ExtractionRequest, OpenAction
from actiongraph.extraction.rule_based import RuleBasedExtractor
from actiongraph.ingestion import load_transcript
from tests.conftest import SAMPLES

TRANSCRIPTS = SAMPLES / "transcripts"


def _extract(filename: str, meeting_date: date, open_actions: list[OpenAction] | None = None):
    transcript = load_transcript(TRANSCRIPTS / filename)
    request = ExtractionRequest(
        transcript=transcript.text,
        meeting_date=meeting_date,
        meeting_title="test",
        open_actions=open_actions or [],
    )
    return RuleBasedExtractor().extract(request).extraction


def test_planning_meeting_actions_and_owners() -> None:
    result = _extract("2026-09-07_sprint-14-planning.txt", date(2026, 9, 7))
    by_task = {a.task: a for a in result.actions}

    assert by_task["Handle the authentication changes"].owner == "Priya"
    assert by_task["Update the API design"].owner == "Team"
    assert by_task["Update the API design"].deadline_text == "by Friday"
    assert by_task["Share the user research"].owner == "Sam"
    # "I'll ..." is attributed to the speaker
    assert by_task["Summarize the top five pain points from the interviews"].owner == "Sam Lee"
    # "Yes, I'll take care of it." is too vague to be an action
    assert not any("care of it" in t for t in by_task)


def test_hedged_suggestion_gets_low_confidence() -> None:
    result = _extract("2026-09-07_sprint-14-planning.txt", date(2026, 9, 7))
    biometric = next(a for a in result.actions if "biometric" in a.task)
    assert biometric.confidence < 0.5


def test_decisions_and_risks() -> None:
    result = _extract("2026-09-07_sprint-14-planning.txt", date(2026, 9, 7))
    assert len(result.decisions) == 2
    assert len(result.risks) == 1  # two risky sentences in one turn -> one risk
    assert result.participants == ["Maya Chen", "Priya Sharma", "Sam Lee", "Alex Kim"]


def test_status_updates_need_open_actions() -> None:
    open_actions = [
        OpenAction(1, "Handle the authentication changes", "Priya Sharma", None, "open"),
        OpenAction(2, "Update the API design", "Team", "by Friday", "open"),
        OpenAction(3, "Share the user research", "Sam Lee", "by Wednesday", "open"),
    ]
    result = _extract("2026-09-14_sprint-14-sync.txt", date(2026, 9, 14), open_actions)
    updates = {u.action_id: u for u in result.status_updates}

    assert updates[1].new_status is ActionStatus.BLOCKED
    assert updates[2].new_status is ActionStatus.DONE
    assert updates[3].new_deadline_text == "next Wednesday"
    # the blocker is linked to the action it blocks
    assert result.risks[0].blocks_task == "Handle the authentication changes"


def test_every_item_quotes_the_transcript() -> None:
    transcript = load_transcript(TRANSCRIPTS / "2026-09-07_sprint-14-planning.txt").text
    result = _extract("2026-09-07_sprint-14-planning.txt", date(2026, 9, 7))
    for item in [*result.actions, *result.decisions, *result.risks]:
        assert item.evidence in transcript
