"""Scoring functions for extraction quality.

Matching predicted items to expected ("gold") items
---------------------------------------------------
Wording differs ("Implement auth changes" vs "Handle the authentication
changes"), so we cannot compare strings exactly. Instead:

1. Score every (gold, predicted) pair with ``similarity()``.
2. Greedily pair the highest-scoring pairs first; each item is used once.
3. Pairs below ``MATCH_THRESHOLD`` do not count as matches.

Then, with TP = matched pairs, FP = unmatched predictions, FN = unmatched gold:

    precision = TP / (TP + FP)   "of what we extracted, how much was right?"
    recall    = TP / (TP + FN)   "of what we should have found, how much did we?"
    F1        = harmonic mean of the two
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from actiongraph.enrichment.entity_resolution import (
    TEAM_ALIASES,
    names_compatible,
    normalize_person_name,
)
from actiongraph.enrichment.text_utils import similarity

MATCH_THRESHOLD = 0.45


@dataclass(frozen=True)
class EvalAction:
    task: str
    owner: str | None
    due_date: date | None


@dataclass(frozen=True)
class Scores:
    true_positives: int
    false_positives: int
    false_negatives: int
    owner_correct: int = 0
    deadline_correct: int = 0

    @property
    def precision(self) -> float:
        predicted = self.true_positives + self.false_positives
        return self.true_positives / predicted if predicted else 1.0

    @property
    def recall(self) -> float:
        expected = self.true_positives + self.false_negatives
        return self.true_positives / expected if expected else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def owner_accuracy(self) -> float:
        return self.owner_correct / self.true_positives if self.true_positives else 0.0

    @property
    def deadline_accuracy(self) -> float:
        return self.deadline_correct / self.true_positives if self.true_positives else 0.0

    def __add__(self, other: Scores) -> Scores:
        return Scores(
            self.true_positives + other.true_positives,
            self.false_positives + other.false_positives,
            self.false_negatives + other.false_negatives,
            self.owner_correct + other.owner_correct,
            self.deadline_correct + other.deadline_correct,
        )


def match_items(
    gold: Sequence[str], predicted: Sequence[str], threshold: float = MATCH_THRESHOLD
) -> list[tuple[int, int, float]]:
    """Greedy one-to-one matching. Returns (gold_index, predicted_index, score) triples."""
    pairs = sorted(
        ((similarity(g, p), gi, pi) for gi, g in enumerate(gold) for pi, p in enumerate(predicted)),
        reverse=True,
    )
    used_gold: set[int] = set()
    used_pred: set[int] = set()
    matches = []
    for score, gi, pi in pairs:
        if score < threshold:
            break
        if gi in used_gold or pi in used_pred:
            continue
        used_gold.add(gi)
        used_pred.add(pi)
        matches.append((gi, pi, score))
    return matches


def owners_match(expected: str | None, predicted: str | None) -> bool:
    if not expected or not predicted:
        return not expected and not predicted
    a, b = normalize_person_name(expected), normalize_person_name(predicted)
    if a in TEAM_ALIASES or b in TEAM_ALIASES:
        return a in TEAM_ALIASES and b in TEAM_ALIASES
    return names_compatible(a, b)


def score_actions(gold: Sequence[EvalAction], predicted: Sequence[EvalAction]) -> Scores:
    matches = match_items([g.task for g in gold], [p.task for p in predicted])
    owner_ok = sum(owners_match(gold[gi].owner, predicted[pi].owner) for gi, pi, _ in matches)
    deadline_ok = sum(gold[gi].due_date == predicted[pi].due_date for gi, pi, _ in matches)
    return Scores(
        true_positives=len(matches),
        false_positives=len(predicted) - len(matches),
        false_negatives=len(gold) - len(matches),
        owner_correct=owner_ok,
        deadline_correct=deadline_ok,
    )


def score_texts(gold: Sequence[str], predicted: Sequence[str]) -> Scores:
    """Precision/recall for items that are just text (decisions, risks)."""
    matches = match_items(gold, predicted)
    return Scores(len(matches), len(predicted) - len(matches), len(gold) - len(matches))


def score_status_updates(gold: dict[int, set[str]], predicted: dict[int, str]) -> Scores:
    """Status updates are matched by action id; the status must be one of the accepted ones.

    ``gold`` maps action id -> acceptable statuses (e.g. {"in_progress", "open"}
    when a postponed item could reasonably be described either way).
    """
    correct = sum(1 for action_id, status in predicted.items() if status in gold.get(action_id, ()))
    return Scores(correct, len(predicted) - correct, len(gold) - correct)
