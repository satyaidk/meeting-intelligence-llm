"""Deadline phrase -> calendar date. Reference meeting: Monday 7 Sep 2026."""

from datetime import date

import pytest

from actiongraph.enrichment.temporal import resolve_deadline
from tests.conftest import MONDAY


def test_reference_date_is_a_monday() -> None:
    assert MONDAY.weekday() == 0  # guards every expectation below


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        # weekdays
        ("by Friday", date(2026, 9, 11)),
        ("Wednesday", date(2026, 9, 9)),
        ("this Thursday", date(2026, 9, 10)),
        ("friday next week", date(2026, 9, 18)),
        ("Friday EOD", date(2026, 9, 11)),
        # relative days
        ("today", MONDAY),
        ("by EOD", MONDAY),
        ("tomorrow", date(2026, 9, 8)),
        ("the day after tomorrow", date(2026, 9, 9)),
        ("in three days", date(2026, 9, 10)),
        ("in 2 weeks", date(2026, 9, 21)),
        ("within 5 business days", date(2026, 9, 14)),
        ("in a month", date(2026, 10, 7)),
        # weeks / months / quarters / years
        ("by end of week", date(2026, 9, 11)),
        ("EOW", date(2026, 9, 11)),
        ("before the weekend", date(2026, 9, 11)),
        ("by end of next week", date(2026, 9, 18)),
        ("end of the month", date(2026, 9, 30)),
        ("end of next month", date(2026, 10, 31)),
        ("end of quarter", date(2026, 9, 30)),
        ("Q4", date(2026, 12, 31)),
        ("end of the year", date(2026, 12, 31)),
        # explicit dates
        ("2026-10-02", date(2026, 10, 2)),
        ("by October 2nd", date(2026, 10, 2)),
        ("Oct 15", date(2026, 10, 15)),
        ("15th of October", date(2026, 10, 15)),
        ("January 5", date(2027, 1, 5)),  # already past this year -> next year
    ],
)
def test_resolves_common_phrases(phrase: str, expected: date) -> None:
    result = resolve_deadline(phrase, MONDAY)
    assert result.due_date == expected, result.rule


@pytest.mark.parametrize(
    "phrase", ["before the next release", "ASAP", "once the credentials arrive", "soon"]
)
def test_phrases_tied_to_unknown_events_stay_unresolved(phrase: str) -> None:
    result = resolve_deadline(phrase, MONDAY)
    assert result.due_date is None
    assert result.has_text
    assert result.confidence == 0.0


def test_no_deadline() -> None:
    result = resolve_deadline(None, MONDAY)
    assert result.due_date is None
    assert not result.has_text


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("next Friday", date(2026, 9, 18)),  # Friday of next week, not this one
        ("next week", date(2026, 9, 18)),
        ("next month", date(2026, 10, 31)),
        ("Monday", date(2026, 9, 14)),  # same weekday as the meeting
    ],
)
def test_ambiguous_phrases_get_low_confidence(phrase: str, expected: date) -> None:
    result = resolve_deadline(phrase, MONDAY)
    assert result.due_date == expected
    assert result.confidence < 0.7  # low enough to be sent to human review


def test_next_weekday_said_late_in_the_week() -> None:
    saturday = date(2026, 9, 12)
    assert resolve_deadline("next Friday", saturday).due_date == date(2026, 9, 18)
    assert resolve_deadline("end of week", saturday).due_date == date(2026, 9, 18)


def test_every_result_explains_itself() -> None:
    assert "Friday" in resolve_deadline("by Friday", MONDAY).rule
