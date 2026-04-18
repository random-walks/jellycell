# Preview environment

jellycell has two "preview" flows depending on what you're developing.

## A. Docs preview (available now)

Live-reload Sphinx dev server:

```bash
make docs
```

Serves at `http://127.0.0.1:8001`. Auto-rebuilds on:

- Edits under `docs/` (any `.md`, `.rst`, `conf.py`).
- Edits under `src/jellycell/` (for `autodoc2` to pick up docstring changes).

Useful while working on:

- Prose changes to file-format, getting-started, etc.
- Docstring authoring (Ruff's D-rules flag missing docstrings; Sphinx renders what you wrote).
- CLI reference (once Phase 1's `sphinxcontrib-typer` directive goes live).

## B. HTML report preview (Phase 3+)

The production preview flow for jellycell's own HTML reports is `jellycell view`. Phase 3 ships the renderer; Phase 4 ships the live viewer (Starlette + SSE + watchfiles). Until Phase 3 lands:

```bash
make preview        # stub; prints instructions
```

For Phase 3 template work specifically (editing `.j2` templates before the server exists), use `sphinx-autobuild`-style ad-hoc scripting; there's no dedicated flow because templates will be exercised by `jellycell view` end-to-end.

## Testing HTML output (Phase 3+)

- **Snapshot**: `pytest-regressions` golden files for deterministic HTML chunks.
- **Structural**: `pytest-playwright` with [ARIA snapshots](https://playwright.dev/python/docs/aria-snapshots) for rendered pages.

Both are added to dev deps in Phase 3.
