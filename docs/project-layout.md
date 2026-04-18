# Project layout

Every jellycell project has a `jellycell.toml` at its root.

## Canonical directory structure

```
my-project/
├── jellycell.toml       # project config (required)
├── notebooks/           # .py source notebooks
├── data/                # input data read by jc.load
├── artifacts/           # outputs written by jc.save / jc.figure / jc.table
├── reports/             # rendered HTML output
├── manuscripts/         # narrative docs + tearsheets (markdown, committed)
└── .jellycell/
    └── cache/           # content-addressed cache (gitignored)
```

All paths are configurable — see the `[paths]` section of `jellycell.toml`.

## Full `jellycell.toml` reference

See [`jellycell.toml.example`](https://github.com/random-walks/jellycell/blob/main/jellycell.toml.example) in the repo root for a commented reference. Sections:

### `[project]`

```toml
[project]
name = "my-project"       # human-readable name; shown in the catalogue
```

### `[paths]`

All paths are relative to the project root. Nothing jellycell writes ever
escapes a declared root (write-guard in `jellycell.paths.Project.resolve`).

```toml
[paths]
notebooks = "notebooks"           # source .py files
data = "data"                     # input data
artifacts = "artifacts"           # output files
reports = "reports"               # rendered HTML
manuscripts = "manuscripts"       # optional prose companions
cache = ".jellycell/cache"        # content-addressed cache
```

### `[run]`

```toml
[run]
kernel = "python3"                # Jupyter kernel name
subprocess = true                 # subprocess-only; in-process is unsupported
timeout_seconds = 600             # per-cell default; `timeout=N` tag overrides
```

### `[viewer]`

Only consumed by `jellycell view` (requires the `[server]` extra).

```toml
[viewer]
host = "127.0.0.1"
port = 5179
watch = ["notebooks", "manuscripts", "artifacts"]     # paths triggering reloads
```

### `[lint]`

Rules with a policy gate. Rules without a gate (like `pep723-position`) always
run.

```toml
[lint]
enforce_artifact_paths = true      # flag jc.save outside paths.artifacts
enforce_declared_deps = false      # flag jc.step cells missing deps=
warn_on_large_cell_output = "10MB" # warn when a cell's cached output exceeds this
```

## File-scope overrides

A notebook's PEP-723 block can override any field at file scope via a
`[tool.jellycell]` table:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas"]
#
# [tool.jellycell]
# timeout_seconds = 1800
# ///
```

The block-scoped value wins for that file. Other `[tool.*]` tables are
preserved unchanged.

## `manuscripts/` — tearsheets and hand-authored writeups

The `manuscripts/` directory holds markdown files that live alongside
notebooks. Two flavors:

- **Auto-generated tearsheets** from `jellycell export tearsheet <nb>` —
  curated one-pagers with prose, inlined figures via relative paths
  (`![](../artifacts/foo.png)`), and JSON summaries flattened into
  two-column tables. The file goes to `manuscripts/<stem>.md` by default;
  override with `--output PATH`. GitHub renders the file inline when you
  browse it — no HTML preview service needed.
- **Hand-authored writeups** (e.g. a paper draft, a decision memo) —
  commit them under a different filename to avoid the tearsheet
  regenerator overwriting your prose. Pattern: keep `tearsheet.md` auto,
  write `paper.md` / `notes.md` / `reviewer-memo.md` by hand. Both can
  reference the same `artifacts/` tree.

Commit `manuscripts/` so reviewers and agents see the latest tearsheet
without re-running anything.

## The `.jellycell/` directory

Auto-created on first run. Usually git-ignored (jellycell's own `.gitignore`
template excludes it).

```
.jellycell/
└── cache/
    ├── blobs/                     # diskcache-backed content-addressed blob store
    ├── manifests/                 # <cache-key>.json per cell execution
    ├── artifacts-index/           # reverse index: artifact sha → producing cell(s)
    └── state.db                   # SQLite catalogue (derived; rebuilt on demand)
```

Filesystem is the source of truth. `jellycell cache rebuild-index` re-scans
manifests if the SQLite index gets corrupted or out of sync.

## Project discovery

`jellycell` walks up from the current directory looking for `jellycell.toml`.
Override with `--project /path/to/root`.

## Tooling

- **Git**: commit `notebooks/`, `data/` (small files; use LFS or external
  storage for large), `artifacts/` if they're outputs worth reviewing,
  `jellycell.toml`. Git-ignore `.jellycell/` and `reports/`.
- **pre-commit**: `jellycell lint` fits cleanly as a pre-commit hook.
- **CI**: run `jellycell run notebooks/*.py` to recompute reports on PR.
