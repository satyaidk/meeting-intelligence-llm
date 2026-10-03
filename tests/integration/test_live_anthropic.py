"""Calls the REAL Anthropic API. Skipped by default because it costs money.

Run with:
    ACTIONGRAPH_LIVE_TESTS=1 pytest -m live          (macOS / Linux / Git Bash)
    $env:ACTIONGRAPH_LIVE_TESTS=1; pytest -m live    (PowerShell)

Assertions are deliberately loose: LLM output varies between runs, so we
check *structure and key facts*, not exact wording. Exact quality is measured
by `actiongraph eval`, not by unit tests.
"""

import os
from datetime import date

import pytest

from actiongraph.config import Settings
from actiongraph.extraction.anthropic_extractor import AnthropicExtractor
from actiongraph.extraction.base import ExtractionRequest
from actiongraph.ingestion import load_transcript
from tests.conftest import SAMPLES

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("ACTIONGRAPH_LIVE_TESTS") != "1",
        reason="set ACTIONGRAPH_LIVE_TESTS=1 to call the real API",
    ),
]


def test_real_extraction_on_sample_meeting() -> None:
    transcript = load_transcript(SAMPLES / "transcripts" / "2026-09-07_sprint-14-planning.txt")
    extractor = AnthropicExtractor.from_settings(Settings())
    result = extractor.extract(
        ExtractionRequest(
            transcript=transcript.text, meeting_date=date(2026, 9, 7), meeting_title="Planning"
        )
    )

    owners = {(a.owner or "").lower() for a in result.extraction.actions}
    assert any("priya" in o for o in owners)
    assert any("sam" in o for o in owners)
    assert len(result.extraction.decisions) >= 1
    assert result.usage is not None and result.usage.output_tokens > 0
    # Precision: the hedged "maybe look at biometric login" should not be a confident action
    assert not any(
        "biometric" in a.task.lower() and a.confidence >= 0.7 for a in result.extraction.actions
    )
