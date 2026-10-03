"""Command-line interface smoke tests (offline provider, temporary database)."""

from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

from actiongraph import cli
from actiongraph.cli import app
from tests.conftest import REPO_ROOT, SAMPLES

runner = CliRunner()


@pytest.fixture(autouse=True)
def wide_console(monkeypatch: pytest.MonkeyPatch) -> None:
    # The test runner's fake terminal is 80 columns, which wraps table cells
    # mid-sentence. A wide console keeps each row on one line for assertions.
    monkeypatch.setattr(cli, "console", Console(width=250))


@pytest.fixture
def demo_db(tmp_path: Path) -> str:
    db = str(tmp_path / "demo.db")
    result = runner.invoke(
        app,
        ["demo", "--provider", "offline", "--db", db, "--samples", str(SAMPLES / "transcripts")],
    )
    assert result.exit_code == 0, result.output
    assert "Cross-meeting timelines" in result.output
    return db


def test_demo_tells_the_cross_meeting_story(demo_db: str) -> None:
    result = runner.invoke(app, ["timeline", "1", "--db", demo_db])
    assert result.exit_code == 0
    assert "open -> blocked" in result.output
    assert "blocked -> done" in result.output


def test_actions_people_and_graph(demo_db: str) -> None:
    assert "Update the API design" in runner.invoke(app, ["actions", "--db", demo_db]).output
    assert "priya s" in runner.invoke(app, ["people", "--db", demo_db]).output
    assert runner.invoke(app, ["graph", "--db", demo_db]).output.startswith("flowchart LR")


def test_review_then_approve(demo_db: str) -> None:
    queue = runner.invoke(app, ["review", "--db", demo_db]).output
    assert "below the review threshold" in queue

    result = runner.invoke(app, ["approve", "action", "6", "--db", demo_db])
    assert result.exit_code == 0
    assert "Approved action 6" in result.output


def test_process_single_file(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "process",
            str(SAMPLES / "other_formats" / "design-review.vtt"),
            "--date",
            "2026-09-22",
            "--provider",
            "offline",
            "--db",
            str(tmp_path / "one.db"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Processed 'Design Review'" in result.output


def test_eval_command() -> None:
    result = runner.invoke(
        app,
        ["eval", "--provider", "offline", "--dataset", str(REPO_ROOT / "evals" / "datasets")],
    )
    assert result.exit_code == 0, result.output
    assert "TOTAL (micro)" in result.output


def test_expected_errors_are_one_red_line(tmp_path: Path) -> None:
    result = runner.invoke(app, ["timeline", "999", "--db", str(tmp_path / "empty.db")])
    assert result.exit_code == 1
    assert "Error: Action item 999 not found" in result.output
    assert "Traceback" not in result.output
