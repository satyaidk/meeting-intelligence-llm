"""Confidence scoring and review routing (human-in-the-loop).

An extracted item is trusted automatically only when *every* signal agrees:

    * the model was confident             (LLM confidence >= threshold)
    * the evidence is really in the text  (grounding)
    * we know exactly who owns it         (entity resolution)
    * we know exactly when it is due      (temporal resolution)

Each failed check adds a plain-English *reason*. Any reason at all sends the
item to the review queue, and the reasons are shown to the reviewer so they
know what to look at. This is deliberately simple: one rule ("any doubt ->
human") is easy to explain, test and tune.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from actiongraph.domain.enums import ReviewStatus
from actiongraph.enrichment.entity_resolution import OwnerResolution, ResolutionMethod
from actiongraph.enrichment.grounding import GroundingResult
from actiongraph.enrichment.temporal import DeadlineResolution

AMBIGUOUS_DEADLINE_CONFIDENCE = 0.7


@dataclass(frozen=True)
class ReviewDecision:
    confidence: float
    status: ReviewStatus
    reasons: tuple[str, ...]

    @property
    def needs_review(self) -> bool:
        return self.status is ReviewStatus.NEEDS_REVIEW


def combined_confidence(llm_confidence: float, grounding: GroundingResult) -> float:
    """Never trust an item more than we can verify its evidence."""
    if grounding.is_grounded:
        return round(llm_confidence, 3)
    return round(min(llm_confidence, grounding.score), 3)


def review_item(
    llm_confidence: float,
    grounding: GroundingResult,
    threshold: float,
    extra_reasons: Iterable[str] = (),
) -> ReviewDecision:
    """Review routing for decisions, risks and status updates."""
    confidence = combined_confidence(llm_confidence, grounding)
    reasons = list(_base_reasons(confidence, grounding, threshold))
    reasons.extend(extra_reasons)
    return _decide(confidence, reasons)


def review_action(
    llm_confidence: float,
    grounding: GroundingResult,
    owner: OwnerResolution,
    deadline: DeadlineResolution,
    threshold: float,
) -> ReviewDecision:
    """Review routing for action items (stricter: they need an owner and a date)."""
    confidence = combined_confidence(llm_confidence, grounding)
    reasons = list(_base_reasons(confidence, grounding, threshold))
    reasons.extend(owner_reasons(owner))
    reasons.extend(deadline_reasons(deadline))
    return _decide(confidence, reasons)


def owner_reasons(owner: OwnerResolution) -> list[str]:
    if owner.method is ResolutionMethod.NONE:
        return ["No owner was identified; unowned work is rarely done."]
    if owner.method is ResolutionMethod.AMBIGUOUS:
        return [f"Owner '{owner.raw}' is ambiguous: could be {', '.join(owner.candidates)}."]
    if owner.method is ResolutionMethod.FUZZY and owner.person is not None:
        return [
            f"Owner '{owner.raw}' was matched to '{owner.person.display_name}' by similar spelling."
        ]
    return []


def deadline_reasons(deadline: DeadlineResolution) -> list[str]:
    if not deadline.has_text:
        return []
    if deadline.due_date is None:
        return [f"Deadline '{deadline.text}' could not be converted to a calendar date."]
    if deadline.confidence < AMBIGUOUS_DEADLINE_CONFIDENCE:
        return [
            f"Deadline '{deadline.text}' was read as {deadline.due_date:%a %d %b %Y} "
            f"({deadline.rule}); please confirm."
        ]
    return []


def _base_reasons(confidence: float, grounding: GroundingResult, threshold: float) -> list[str]:
    reasons = []
    if not grounding.is_grounded:
        reasons.append(
            f"Evidence quote not found in the transcript (match {grounding.score:.0%}); "
            "the model may have paraphrased or invented it."
        )
    if confidence < threshold:
        reasons.append(
            f"Confidence {confidence:.2f} is below the review threshold {threshold:.2f}."
        )
    return reasons


def _decide(confidence: float, reasons: list[str]) -> ReviewDecision:
    status = ReviewStatus.NEEDS_REVIEW if reasons else ReviewStatus.AUTO_APPROVED
    return ReviewDecision(confidence=confidence, status=status, reasons=tuple(reasons))
