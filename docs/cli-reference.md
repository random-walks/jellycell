# CLI reference

Every command supports `--json` for machine-readable output with
`schema_version: 1` (spec §10.1 contract).

## Global flags

- `--project PATH` / `-p PATH` — project root override. Default: discover by
  walking up from cwd for `jellycell.toml`.
- `--quiet` / `-q` — reduce output.
- `--verbose` / `-V` — increase output.
- `--json` — emit JSON to stdout (one object per command).
- `--version` — print version and exit.

## Auto-generated reference

```{typer} jellycell.cli.app:app
:prog: jellycell
:width: 100
```

## Command details

### `jellycell init <path>`

Scaffold a new project.

```bash
jellycell init my-analysis --name my-analysis
```

Flags:
- `--name NAME` — project name. Defaults to the target dir name.
- `--force` — overwrite an existing `jellycell.toml`.

JSON output (example structure):

```
{"schema_version": 1, "path": "/abs/path", "name": "my-project", "created": ["jellycell.toml", "notebooks/", ...]}
```

### `jellycell lint [path]`

Check project against lint rules. Returns exit code 1 on violations.

```bash
jellycell lint              # discover project from cwd
jellycell lint --fix        # apply auto-fixes
jellycell --json lint       # JSON report
```

### `jellycell run <notebook>`

Execute a notebook end-to-end with caching.

```bash
jellycell run notebooks/foo.py
jellycell run notebooks/foo.py --force    # re-execute all cells
```

### `jellycell render [notebook]`

Render HTML reports.

```bash
jellycell render                              # all notebooks + index
jellycell render notebooks/foo.py             # single notebook
jellycell render --standalone                 # inline images (one-file HTML)
```

### `jellycell view`

Serve the live catalogue (requires `[server]` extra).

```bash
jellycell view                                # use [viewer] config
jellycell view --host 0.0.0.0 --port 8080
```

### `jellycell cache ...`

- `cache list` — show cached cell executions.
- `cache prune [--older-than DURATION] [--keep-last N] [--dry-run]` — remove old entries.
- `cache clear [-y]` — wipe the cache.
- `cache rebuild-index` — re-scan manifests to rebuild SQLite index.

### `jellycell export <format> <notebook>`

- `export ipynb` — `.ipynb` with cached outputs reattached.
- `export md` — MyST markdown (full notebook + every cell's outputs).
- `export tearsheet [-o PATH]` — curated markdown tearsheet. Defaults to
  `manuscripts/<stem>.md`. Includes markdown narration, inlined image
  artifacts via relative paths, and JSON summaries flattened as
  two-column tables. Safe to commit; GitHub renders it inline.

### `jellycell new <name>`

Scaffold a new notebook under `notebooks/`.

```bash
jellycell new analysis        # creates notebooks/analysis.py
```

### `jellycell prompt`

Emit the canonical [agent guide](agent-guide.md) to stdout.

```bash
jellycell prompt | pbcopy
```
