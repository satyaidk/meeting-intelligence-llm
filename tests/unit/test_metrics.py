"""Evaluation metrics: matching, precision, recall, F1."""

from datetime import date

import pytest

from actiongraph.enrichment.text_utils import similarity
from actiongraph.evaluation.metrics import (
    EvalAction,
    Scores,
    match_items,
    owners_match,
    score_actions,
    score_status_updates,
)


def test_similarity_tolerates_rewording() -> None:
    assert similarity("Share the user research", "share user research") > 0.8
    assert (
        similarity("Implement authentication changes", "Handle the authentication changes") > 0.45
    )
    assert similarity("Share the user research", "Set up staging") < 0.4


def test_similarity_is_lexical_not_semantic() -> None:
    # A known limitation, documented in docs/guides/EVALUATION.md: abbreviations
    # and synonyms are not understood. Embeddings or an LLM judge would fix this.
    assert similarity("Implement auth changes", "Handle the authentication changes") < 0.45


def test_matching_is_one_to_one() -> None:
    gold = ["Share the user research", "Update the API design"]
    predicted = ["Update API design", "Share research with users", "Order pizza"]
    matches = {(g, p) for g, p, _ in match_items(gold, predicted)}
    assert matches == {(0, 1), (1, 0)}


def test_precision_recall_f1() -> None:
    scores = Scores(true_positives=3, false_positives=1, false_negatives=2)
    assert scores.precision == pytest.approx(0.75)
    assert scores.recall == pytest.approx(0.6)
    assert scores.f1 == pytest.approx(2 * 0.75 * 0.6 / 1.35)


def test_empty_sets_are_perfect_not_division_errors() -> None:
    scores = Scores(0, 0, 0)
    assert scores.precision == 1.0
    assert scores.recall == 1.0


@pytest.mark.parametrize(
    ("expected", "predicted", "ok"),
    [
        ("Priya Sharma", "Priya", True),
        ("Priya Sharma", "@priya", True),
        ("Team", "we", True),
        ("Team", "Priya", False),
        (None, None, True),
        ("Sam Lee", None, False),
    ],
)
def test_owner_matching(expected: str | None, predicted: str | None, ok: bool) -> None:
    assert owners_match(expected, predicted) is ok


def test_score_actions_counts_owner_and_deadline_accuracy() -> None:
    gold = [
        EvalAction("Share the user research", "Sam Lee", date(2026, 9, 9)),
        EvalAction("Update the API design", "Team", date(2026, 9, 11)),
    ]
    predicted = [
        EvalAction("Share user research", "Sam", date(2026, 9, 9)),
        EvalAction("Update the API design", "Alex", None),
        EvalAction("Book a room", None, None),
    ]
    scores = score_actions(gold, predicted)
    assert (scores.true_positives, scores.false_positives, scores.false_negatives) == (2, 1, 0)
    assert scores.owner_accuracy == 0.5
    assert scores.deadline_accuracy == 0.5


def test_status_update_scoring_accepts_alternatives() -> None:
    gold = {1: {"blocked"}, 3: {"in_progress", "open"}}
    scores = score_status_updates(gold, {1: "blocked", 3: "open", 9: "done"})
    assert (scores.true_positives, scores.false_positives, scores.false_negatives) == (2, 1, 0)
