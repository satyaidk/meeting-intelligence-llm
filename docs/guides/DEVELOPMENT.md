# Development guide

How to work on ActionGraph day to day: commands, workflow, conventions, and a
worked example of adding a feature end to end.

## Everyday commands

| Task | Command |
|------|---------|
| Run all tests | `pytest` |
| Run one file / one test | `pytest tests/unit/test_temporal.py` · `pytest -k next_friday` |
| Tests with coverage | `pytest --cov --cov-report=term-missing` |
| Lint (find problems) | `ruff check src tests` |
| Auto-fix lint + format | `ruff check src tests --fix` then `ruff format src tests` |
| Run the API with auto-reload | `actiongraph serve --reload` |
| Measure extraction quality | `actiongraph eval --provider offline` (free) / `--provider anthropic` |
| Reset local data | delete the `data/` folder |

CI (`.github/workflows/ci.yml`) runs `ruff check`, `ruff format --check`
and `pytest` on every push and pull request. Run the same three locally before
you push.

## Workflow (the way most teams work)

```text
main  ─────●─────────────●──────────────●────►
            \           /                /
             feat/overdue-actions ──●──●   (PR, review, CI green, squash-merge)
```

1. **Branch** from `main`: `git switch -c feat/overdue-actions`
   (prefixes: `feat/`, `fix/`, `docs/`, `refactor/`, `test/`, `chore/`).
2. **Write a failing test** that describes the behaviour you want.
3. **Make it pass** with the smallest reasonable change.
4. **Refactor** while the tests stay green.
5. **Update docs** in the same branch (README, a guide, or an ADR for a significant decision).
6. **Commit** with a [Conventional Commits](https://www.conventionalcommits.org/) message:
   `feat(api): add GET /api/actions/overdue`.
7. **Open a pull request**; fill in the template; CI must be green.
8. **Address review**, then squash-merge.

## Code conventions

- **Layers:** respect the dependency rule in [ARCHITECTURE.md](../architecture/ARCHITECTURE.md#2-layers). Business logic does not go in API routes or the CLI.
- **Pure functions first:** put logic in `enrichment/` (or a similar pure module) where it can be unit-tested without a database.
- **Types everywhere:** all functions have type hints; prefer dataclasses/Pydantic models over loose dicts.
- **Errors:** raise a subclass of `ActionGraphError` for expected failures; let unexpected errors (bugs) propagate.
- **No `print` in library code:** use `logging.getLogger(__name__)`. The CLI prints via Rich.
- **Comments explain *why*,** not *what*. Module docstrings explain the purpose of the file.
- **Style:** enforced by `ruff` (line length 100). Do not argue with the formatter.

## Worked example: add "overdue actions"

**Goal:** `GET /api/actions/overdue` returns open actions whose `due_date` is before today.

1. **Repository query** (`storage/repository.py`):
   ```python
   def overdue_actions(self, today: date) -> Sequence[ActionItem]:
       return self.session.scalars(
           select(ActionItem)
           .where(ActionItem.status.not_in(CLOSED_STATUSES))
           .where(ActionItem.review_status != ReviewStatus.REJECTED)
           .where(ActionItem.due_date < today)
           .order_by(ActionItem.due_date)
       ).all()
   ```
   Note the `today` parameter: passing time in (instead of calling
   `date.today()` inside) makes the function testable.

2. **Route** (`api/routes/actions.py`). Declare it *before* `/{action_id}`
   so FastAPI does not try to parse `"overdue"` as an id:
   ```python
   @router.get("/overdue", response_model=list[ActionOut])
   def overdue(session: Session = Depends(get_session)) -> list[ActionOut]:
       return [ActionOut.model_validate(a) for a in Repository(session).overdue_actions(date.today())]
   ```

3. **Tests**: a repository test with a fixed `today`, and an API test in `tests/integration/test_api.py`.

4. **Docs**: add the endpoint to [API_REFERENCE.md](../api/API_REFERENCE.md) and a line to `CHANGELOG.md`.

## Changing the LLM behaviour

Prompt or schema changes are *behaviour changes* and need evidence:

1. Run `actiongraph eval --provider anthropic` on `main` and save the table.
2. Make **one** change (prompt wording, a schema description, effort level).
3. Run the eval again and compare. Include both tables in the PR description.

See [PROMPT_ENGINEERING.md](PROMPT_ENGINEERING.md) and [EVALUATION.md](EVALUATION.md).

## Database changes

There are no migrations yet (`init_db` calls `create_all`, which only creates
*missing* tables). After changing `storage/models.py` during development,
delete `data/*.db`. Before any real deployment, introduce Alembic; that
decision deserves an ADR.
