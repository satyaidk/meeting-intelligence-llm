"""Command-line interface.

    actiongraph demo --provider offline     process the three sample meetings
    actiongraph process FILE                process one meeting file
    actiongraph actions | timeline ID       browse the tracker
    actiongraph review | approve | reject   human-in-the-loop
    actiongraph graph                       print the graph as Mermaid
    actiongraph eval --provider offline     score extraction quality
    actiongraph serve                       start the API + web UI

Run ``actiongraph COMMAND --help`` for details on any command.
"""

from __future__ import annotations

import functools
import os
import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy.orm import Session

from actiongraph.config import Settings, get_settings
from actiongraph.domain.enums import ActionStatus, ItemKind
from actiongraph.errors import ActionGraphError
from actiongraph.extraction import build_extractor
from actiongraph.ingestion import load_transcript
from actiongraph.logging_setup import configure_logging
from actiongraph.services import MeetingProcessor, ProcessingReport, ReviewService
from actiongraph.storage import Repository, create_db_engine, init_db, make_session_factory

app = typer.Typer(
    help="ActionGraph: turn meeting conversations into trackable, reviewable work.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)
console = Console()

ProviderOpt = Annotated[
    str | None,
    typer.Option(
        "--provider", "-p", help="anthropic | offline (overrides ACTIONGRAPH_LLM_PROVIDER)"
    ),
]
DbOpt = Annotated[
    str | None,
    typer.Option("--db", help="SQLite file or SQLAlchemy URL (overrides the .env value)"),
]

_STATUS_STYLE = {
    "open": "white", "in_progress": "cyan", "blocked": "bold red", "done": "green",
    "cancelled": "dim", "needs_review": "yellow", "auto_approved": "green",
    "approved": "green", "rejected": "dim",
}  # fmt: skip


# ----------------------------------------------------------------- helpers
def _handle_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Show expected errors as one red line instead of a stack trace."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except ActionGraphError as exc:
            console.print(f"[bold red]Error:[/] {exc}")
            raise typer.Exit(code=1) from None

    return wrapper


def _settings(provider: str | None = None, db: str | None = None) -> Settings:
    updates: dict[str, Any] = {}
    if provider:
        if provider not in ("anthropic", "offline"):
            raise typer.BadParameter("provider must be 'anthropic' or 'offline'")
        updates["llm_provider"] = provider
    if db:
        updates["database_url"] = db if "://" in db else f"sqlite:///{db}"
    settings = get_settings().model_copy(update=updates)
    configure_logging(settings.log_level)
    return settings


@contextmanager
def _session(settings: Settings) -> Iterator[Session]:
    engine = create_db_engine(settings.database_url)
    init_db(engine)
    with make_session_factory(engine)() as session:
        yield session


def _style(value: str) -> str:
    return f"[{_STATUS_STYLE.get(value, 'white')}]{value}[/]"


def _meeting_info_from_filename(path: Path) -> tuple[date | None, str]:
    """'2026-09-07_sprint-14-planning.txt' -> (2026-09-07, 'Sprint 14 Planning')."""
    match = re.match(r"(\d{4}-\d{2}-\d{2})[_\- ]?(.*)", path.stem)
    if not match:
        return None, path.stem.replace("_", " ").replace("-", " ").title()
    title = match.group(2).replace("_", " ").replace("-", " ").title() or "Meeting"
    return date.fromisoformat(match.group(1)), title


def _print_report(report: ProcessingReport, title: str) -> None:
    console.print(
        f"[bold]Processed '{title}'[/] -> meeting #{report.meeting_id} "
        f"([dim]{report.provider}/{report.model}, {report.latency_seconds:.1f}s[/])"
    )
    console.print(
        f"  {report.actions_created} actions, {report.decisions_created} decisions, "
        f"{report.risks_created} risks | {report.status_updates_applied} status updates applied, "
        f"{report.status_updates_pending} pending | {report.duplicates_merged} duplicates merged | "
        f"[yellow]{report.items_needing_review} need review[/]"
    )
    if report.usage:
        console.print(
            f"  [dim]tokens: {report.usage.input_tokens} in / {report.usage.output_tokens} out "
            f"({report.usage.cache_read_input_tokens} read from cache)[/]"
        )
    for warning in report.warnings:
        console.print(f"  [yellow]warning:[/] {warning}")


def _actions_table(session: Session, status: str | None = None) -> Table:
    table = Table(title="Action items", show_lines=False)
    for column in ("#", "Task", "Owner", "Due", "Status", "Review", "Conf."):
        table.add_column(column)
    for a in Repository(session).list_actions(status=status):
        table.add_row(
            str(a.id),
            a.task,
            a.owner_name or "[dim]-[/]",
            f"{a.due_date:%a %d %b}" if a.due_date else (a.deadline_text or "[dim]-[/]"),
            _style(a.status),
            _style(a.review_status),
            f"{a.confidence:.2f}",
        )
    return table


def _print_timeline(session: Session, action_id: int) -> None:
    action = Repository(session).get_action(action_id)
    console.print(f"[bold]#{action.id} {action.task}[/] (owner: {action.owner_name or '-'})")
    for e in action.events:
        when = f"{e.meeting.meeting_date}" if e.meeting else f"{e.created_at:%Y-%m-%d}"
        where = e.meeting.title if e.meeting else "manual edit"
        change = (
            f"{e.from_status} -> {e.to_status}" if e.from_status and e.from_status != e.to_status
            else (e.to_status or "")
        )  # fmt: skip
        pending = "" if e.applied else f" [yellow]({e.review_status}, not applied)[/]"
        console.print(f"   {when}  {where:<28} {e.event_type:<17} {change}{pending}")
        if e.event_type != "created" and e.evidence:
            console.print(f'   [dim]{"":10}  "{e.evidence}"[/]')


# ---------------------------------------------------------------- commands
@app.command()
@_handle_errors
def process(
    file: Annotated[Path, typer.Argument(help="Transcript (.txt/.vtt/.srt/.json) or audio file")],
    title: Annotated[
        str | None, typer.Option(help="Meeting title (default: from file name)")
    ] = None,
    meeting_date: Annotated[
        str | None, typer.Option("--date", help="YYYY-MM-DD (default: from file name, else today)")
    ] = None,
    provider: ProviderOpt = None,
    db: DbOpt = None,
) -> None:
    """Process one meeting file and store the results."""
    settings = _settings(provider, db)
    name_date, name_title = _meeting_info_from_filename(file)
    when = date.fromisoformat(meeting_date) if meeting_date else (name_date or date.today())
    title = title or name_title

    transcript = load_transcript(
        file, whisper_model=settings.whisper_model, whisper_device=settings.whisper_device
    )
    with _session(settings) as session:
        processor = MeetingProcessor(session, build_extractor(settings), settings.review_threshold)
        report = processor.process(transcript, title=title, meeting_date=when)
    _print_report(report, title)


@app.command()
@_handle_errors
def demo(
    provider: ProviderOpt = None,
    db: Annotated[
        str, typer.Option("--db", help="Demo database file (reset each run)")
    ] = "data/demo.db",
    samples: Annotated[Path, typer.Option(help="Folder of sample transcripts")] = Path(
        "samples/transcripts"
    ),
) -> None:
    """Reset a demo database and process the sample meetings in date order."""
    files = sorted(samples.glob("*.txt"))
    if not files:
        raise ActionGraphError(f"No .txt transcripts found in {samples} (run from the repo root).")
    db_path = Path(db)
    if db_path.exists():
        db_path.unlink()
    settings = _settings(provider, str(db_path))
    extractor = build_extractor(settings)

    with _session(settings) as session:
        for file in files:
            when, title = _meeting_info_from_filename(file)
            transcript = load_transcript(file)
            report = MeetingProcessor(session, extractor, settings.review_threshold).process(
                transcript, title=title, meeting_date=when or date.today()
            )
            _print_report(report, title)
            console.print()

        console.print(_actions_table(session))
        console.print("\n[bold]Cross-meeting timelines[/] (actions that changed after creation)\n")
        for action in Repository(session).list_actions():
            if len(action.events) > 1:
                _print_timeline(session, action.id)
                console.print()
        pending = sum(len(v) for v in ReviewService(session).queue().values())
        console.print(
            f"[yellow]{pending} item(s) are waiting for review.[/] "
            f"Try: actiongraph review --db {db}"
        )


@app.command()
@_handle_errors
def actions(
    status: Annotated[ActionStatus | None, typer.Option(help="Filter by status")] = None,
    db: DbOpt = None,
) -> None:
    """List tracked action items."""
    with _session(_settings(db=db)) as session:
        console.print(_actions_table(session, status))


@app.command()
@_handle_errors
def timeline(action_id: int, db: DbOpt = None) -> None:
    """Show one action's history across meetings."""
    with _session(_settings(db=db)) as session:
        _print_timeline(session, action_id)


@app.command()
@_handle_errors
def review(db: DbOpt = None) -> None:
    """Show everything waiting for human review, with the reasons."""
    with _session(_settings(db=db)) as session:
        queue = ReviewService(session).queue()
        total = sum(len(items) for items in queue.values())
        if not total:
            console.print("[green]The review queue is empty.[/]")
            return
        for kind, items in queue.items():
            for item in items:
                console.print(
                    f"[bold]{kind.value} {item.id}[/] {_review_label(kind, item)}  "
                    f"[dim](conf {item.confidence:.2f})[/]",
                    highlight=False,
                )
                for reason in item.review_reasons:
                    console.print(f"    [yellow]- {reason}[/]", highlight=False)
        console.print(f"\n{total} item(s). Approve or reject with: actiongraph approve action 3")


def _review_label(kind: ItemKind, item: Any) -> str:
    if kind is ItemKind.ACTION:
        due = item.due_date or item.deadline_text or "-"
        return f"{item.task} (owner: {item.owner_name or '-'}, due: {due})"
    if kind is ItemKind.DECISION:
        return item.text
    if kind is ItemKind.RISK:
        return f"\\[{item.kind}] {item.description}"
    change = f"{item.from_status} -> {item.to_status}"
    if item.deadline_text:
        change += f", deadline '{item.deadline_text}'"
    return f"update to #{item.action_id} '{item.action_task}': {change}"


@app.command()
@_handle_errors
def approve(kind: ItemKind, item_id: int, db: DbOpt = None) -> None:
    """Approve a reviewed item (applies pending status updates)."""
    with _session(_settings(db=db)) as session:
        ReviewService(session).approve(kind, item_id)
    console.print(f"[green]Approved {kind.value} {item_id}.[/]")


@app.command()
@_handle_errors
def reject(kind: ItemKind, item_id: int, db: DbOpt = None) -> None:
    """Reject an item the extractor got wrong."""
    with _session(_settings(db=db)) as session:
        ReviewService(session).reject(kind, item_id)
    console.print(f"[dim]Rejected {kind.value} {item_id}.[/]")


@app.command()
@_handle_errors
def people(db: DbOpt = None) -> None:
    """List people and every spelling of their name that was merged."""
    with _session(_settings(db=db)) as session:
        table = Table(title="People")
        for column in ("#", "Name", "Known as"):
            table.add_column(column)
        for p in Repository(session).list_people():
            table.add_row(str(p.id), p.display_name, ", ".join(sorted(a.alias for a in p.aliases)))
        console.print(table)


@app.command()
@_handle_errors
def graph(
    output: Annotated[Path | None, typer.Option(help="Write to a file instead of stdout")] = None,
    db: DbOpt = None,
) -> None:
    """Print the ActionGraph as a Mermaid diagram."""
    from actiongraph.graph import build_graph

    with _session(_settings(db=db)) as session:
        mermaid = build_graph(session).to_mermaid()
    if output:
        output.write_text(f"```mermaid\n{mermaid}\n```\n", encoding="utf-8")
        console.print(f"Wrote {output}")
    else:
        print(mermaid)


@app.command("eval")
@_handle_errors
def evaluate(
    provider: ProviderOpt = None,
    dataset: Annotated[Path, typer.Option(help="Folder of golden JSON cases")] = Path(
        "evals/datasets"
    ),
) -> None:
    """Score extraction quality (precision / recall / F1) on the golden dataset."""
    from actiongraph.evaluation.runner import run_eval, total

    settings = _settings(provider)
    results = run_eval(dataset, build_extractor(settings))
    if not results:
        raise ActionGraphError(f"No evaluation cases found in {dataset}")

    table = Table(title=f"Extraction quality - provider: {settings.llm_provider}")
    for column in ("Case", "Action P", "Action R", "Action F1", "Owner acc", "Deadline acc",
                   "Update F1", "Decision F1", "Risk F1"):  # fmt: skip
        table.add_column(column, justify="right")
    rows = [(r.case_id, r.actions, r.updates, r.decisions, r.risks, r.error) for r in results]
    rows.append(("TOTAL (micro)", total(results, "actions"), total(results, "updates"),
                 total(results, "decisions"), total(results, "risks"), None))  # fmt: skip
    for name, act, upd, dec, risk, error in rows:
        if error:
            table.add_row(name, f"[red]{error}[/]", *[""] * 7)
            continue
        table.add_row(
            name, f"{act.precision:.2f}", f"{act.recall:.2f}", f"{act.f1:.2f}",
            f"{act.owner_accuracy:.2f}", f"{act.deadline_accuracy:.2f}",
            f"{upd.f1:.2f}", f"{dec.f1:.2f}", f"{risk.f1:.2f}",
        )  # fmt: skip
    console.print(table)
    console.print(
        "[dim]P = precision, R = recall. Owner/deadline accuracy are measured on matched "
        "actions only. See docs/guides/EVALUATION.md.[/]"
    )


@app.command()
def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: Annotated[bool, typer.Option(help="Restart on code changes (development)")] = False,
    provider: ProviderOpt = None,
    db: DbOpt = None,
) -> None:
    """Start the REST API and web UI (http://127.0.0.1:8000)."""
    import uvicorn

    # The server builds its own settings from the environment, so pass overrides that way.
    if provider:
        os.environ["ACTIONGRAPH_LLM_PROVIDER"] = provider
    if db:
        os.environ["ACTIONGRAPH_DATABASE_URL"] = db if "://" in db else f"sqlite:///{db}"
    get_settings.cache_clear()
    console.print(
        f"ActionGraph UI: [bold]http://{host}:{port}[/]   API docs: http://{host}:{port}/docs"
    )
    uvicorn.run("actiongraph.api.app:create_app", factory=True, host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
