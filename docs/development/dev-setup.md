# Dev setup

## Prerequisites

- Python 3.11+ (3.12 recommended).
- [uv](https://docs.astral.sh/uv/) — fastest way to manage the dev env. `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`.
- Make — macOS/Linux ship with it; on Windows use WSL or [`just`](https://github.com/casey/just).
- For integration tests: `ipykernel` (installed automatically via dev deps).

## First-time setup

```bash
git clone https://github.com/random-walks/jellycell
cd jellycell
make dev
```

`make dev` runs `uv sync --all-extras` (installs runtime + server + docs + dev deps) and `uv run pre-commit install` (enables ruff/mypy on commit).

## Dev loop

```bash
make test            # full pytest suite
make test-unit       # fast unit tests only
make lint            # ruff + mypy
make format          # ruff format + fix lint issues
make docs            # sphinx-autobuild at http://127.0.0.1:8001
```

## Running the CLI during dev

Once Phase 1 lands:

```bash
uv run jellycell --help
uv run python -m jellycell --version
```

## Debugging

- Failing pytest run: `uv run pytest -x -vv` stops at the first failure with full tracebacks.
- Failing mypy: `uv run mypy src --show-error-codes` to enable per-error silencing.
- Stuck kernel in integration tests: ctrl-c once, pytest cleans up via `pytest-asyncio` fixtures.

## Editor config

VS Code: install the official Python, Pylance, and Ruff extensions. Point the interpreter at `.venv/bin/python` (created by `uv sync`).
