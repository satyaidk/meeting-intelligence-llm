"""The evaluation harness runs end to end on the golden dataset (offline baseline)."""

from actiongraph.evaluation.runner import load_cases, run_eval, total
from actiongraph.extraction.rule_based import RuleBasedExtractor
from tests.conftest import REPO_ROOT

DATASET = REPO_ROOT / "evals" / "datasets"


def test_dataset_loads_and_paths_exist() -> None:
    cases = load_cases(DATASET)
    assert len(cases) >= 5
    for case in cases:
        assert case.transcript_path.exists(), case.transcript_path


def test_offline_baseline_scores() -> None:
    results = run_eval(DATASET, RuleBasedExtractor())
    assert all(r.error is None for r in results)

    actions = total(results, "actions")
    # A regression guard for the baseline, not a quality target.
    assert actions.recall >= 0.6
    assert 0.0 <= actions.precision <= 1.0
