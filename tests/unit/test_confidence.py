"""Review routing: when does a human need to look at an item?"""

from actiongraph.domain.enums import ReviewStatus
from actiongraph.enrichment.confidence import review_action, review_item
from actiongraph.enrichment.entity_resolution import (
    KnownPerson,
    OwnerResolution,
    ResolutionMethod,
)
from actiongraph.enrichment.grounding import GroundingResult
from actiongraph.enrichment.temporal import resolve_deadline
from tests.conftest import MONDAY

PRIYA = OwnerResolution(
    "Priya", KnownPerson("1", "Priya Sharma", {"priya"}), ResolutionMethod.EXACT, 1.0
)
GROUNDED = GroundingResult(1.0)
THRESHOLD = 0.7


def test_confident_complete_action_is_auto_approved() -> None:
    result = review_action(0.95, GROUNDED, PRIYA, resolve_deadline("by Friday", MONDAY), THRESHOLD)
    assert result.status is ReviewStatus.AUTO_APPROVED
    assert result.reasons == ()


def test_low_confidence_goes_to_review() -> None:
    result = review_action(0.5, GROUNDED, PRIYA, resolve_deadline(None, MONDAY), THRESHOLD)
    assert result.needs_review
    assert "below the review threshold" in result.reasons[0]


def test_ungrounded_evidence_caps_confidence() -> None:
    result = review_item(0.99, GroundingResult(0.3), THRESHOLD)
    assert result.confidence == 0.3  # never trust more than we can verify
    assert result.needs_review
    assert any("not found in the transcript" in r for r in result.reasons)


def test_missing_owner_goes_to_review() -> None:
    nobody = OwnerResolution(None, None, ResolutionMethod.NONE, 0.0)
    result = review_action(0.95, GROUNDED, nobody, resolve_deadline(None, MONDAY), THRESHOLD)
    assert any("No owner" in r for r in result.reasons)


def test_team_owner_is_fine() -> None:
    team = OwnerResolution("Team", None, ResolutionMethod.TEAM, 1.0)
    result = review_action(0.95, GROUNDED, team, resolve_deadline(None, MONDAY), THRESHOLD)
    assert result.status is ReviewStatus.AUTO_APPROVED


def test_ambiguous_owner_lists_candidates() -> None:
    ambiguous = OwnerResolution(
        "Priya", None, ResolutionMethod.AMBIGUOUS, 0.3, ("Priya Kumar", "Priya Sharma")
    )
    result = review_action(0.95, GROUNDED, ambiguous, resolve_deadline(None, MONDAY), THRESHOLD)
    assert "Priya Kumar, Priya Sharma" in result.reasons[0]


def test_unresolvable_deadline_goes_to_review() -> None:
    deadline = resolve_deadline("before the next release", MONDAY)
    result = review_action(0.95, GROUNDED, PRIYA, deadline, THRESHOLD)
    assert any("could not be converted" in r for r in result.reasons)


def test_ambiguous_deadline_asks_for_confirmation() -> None:
    deadline = resolve_deadline("next Friday", MONDAY)
    result = review_action(0.95, GROUNDED, PRIYA, deadline, THRESHOLD)
    assert any("please confirm" in r for r in result.reasons)


def test_extra_reasons_are_included() -> None:
    result = review_item(0.95, GROUNDED, THRESHOLD, extra_reasons=["Custom reason."])
    assert result.reasons == ("Custom reason.",)
