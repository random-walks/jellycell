# Preview environment

jellycell has two "preview" flows depending on what you're developing.

## A. Docs preview

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
- CLI reference (driven by `sphinxcontrib-typer`).

## B. HTML report preview

The production preview flow for jellycell's own HTML reports is `jellycell view` — see the [examples/](https://github.com/random-walks/jellycell/tree/main/examples) projects for real material to serve:

```bash
cd examples/demo
jellycell view    # requires [server] extra; live-reloads on file changes
```

For template work specifically (editing `.j2` templates), run `jellycell render` in an example project to produce static HTML and reload your browser, or keep `jellycell view` open — it re-renders on template edits thanks to `watchfiles`.

## Testing HTML output

- **Snapshot**: `pytest-regressions` golden files for deterministic HTML chunks — see `tests/integration/test_json_schemas.py` for the pattern.
- **Parity**: `tests/integration/test_render_parity.py` asserts static render and server render are byte-equal.
- **SSE end-to-end**: `tests/integration/test_server_sse_e2e.py` spawns a real uvicorn server and asserts reload events propagate.
