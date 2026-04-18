# CLI reference

Every command supports `--json` for machine-readable output with
`schema_version: 1` ([§10.1 contract](reference/contracts.md#10-1-json-schemas)).

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
jellycell run notebooks/foo.py --force                    # re-execute all cells
jellycell run notebooks/foo.py -m "fixed sign error"      # journal entry message
```

After the run, `jellycell run` warns about any artifact larger than
`[artifacts] max_committed_size_mb` (default 50) with `.gitignore` / Git
LFS guidance. Set the threshold to `0` in `jellycell.toml` to silence.

When `[journal] enabled = true` (the default) a one-section entry is
appended to `manuscripts/journal.md` — timestamp + cell summary +
artifact changes + your `-m` message. Append-only; hand-edits survive.

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
  `manuscripts/tearsheets/<stem>.md` so the auto-generated subfolder stays
  separate from hand-authored writeups at the root of `manuscripts/`.
  Includes markdown narration, inlined image artifacts via relative
  paths, JSON summaries flattened as two-column tables, and a header
  link to `reports/<stem>.html` when it exists. Safe to commit; GitHub
  renders it inline.

### `jellycell checkpoint ...`

Bundle reproducible project snapshots (self-contained `.tar.gz`).
Default target on `restore` is a **new sibling directory** — the live
project is never touched unless you explicitly pass `--into` + `--force`.

```bash
jellycell checkpoint create                       # auto-timestamped name
jellycell checkpoint create --name v1-draft -m "submitted for review"
jellycell checkpoint list                         # newest first
jellycell checkpoint restore v1-draft             # → <project>-restored-v1-draft/
jellycell checkpoint restore v1-draft --into /tmp/inspect --force
```

The archive includes `notebooks/`, `data/`, `artifacts/`, `reports/`,
`manuscripts/`, `jellycell.toml`, and `.jellycell/cache/` — so a
reviewer who unpacks it can re-render HTML without a re-run. Junk
dirs (`__pycache__`, `.venv`, `.git`, etc.) are skipped. Sidecar
`<name>.json` metadata (created_at, message, file count) sits next to
each `.tar.gz` so `list` is fast.

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
