"""Is the evidence quote really in the transcript?"""

from actiongraph.enrichment.grounding import ground_evidence

TRANSCRIPT = """\
Maya Chen: We'll, um, update the API design by Friday so the backend team can review it.
Sam Lee: I'll share the user research by Wednesday."""


def test_exact_quote_scores_one() -> None:
    assert ground_evidence("I'll share the user research by Wednesday.", TRANSCRIPT).score == 1.0


def test_case_and_punctuation_are_ignored() -> None:
    result = ground_evidence("i'll SHARE the user-research by wednesday", TRANSCRIPT)
    assert result.score >= 0.8
    assert result.is_grounded


def test_dropped_filler_word_is_still_grounded() -> None:
    result = ground_evidence("We'll update the API design by Friday", TRANSCRIPT)
    assert result.is_grounded


def test_invented_quote_is_not_grounded() -> None:
    result = ground_evidence("Priya agreed to rewrite the billing service by Monday", TRANSCRIPT)
    assert not result.is_grounded
    assert result.score < 0.5


def test_empty_evidence() -> None:
    assert ground_evidence("", TRANSCRIPT).score == 0.0
