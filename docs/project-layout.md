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

### `[artifacts]`

Controls where path-less `jc.figure()` / `jc.table()` calls save, and
when jellycell warns about outsized outputs. Explicit paths in
`jc.save(x, "artifacts/foo.json")` always win — the layout setting is
only consulted when jellycell picks the location.

```toml
[artifacts]
layout = "flat"                   # "flat" | "by_notebook" | "by_cell"
max_committed_size_mb = 50        # post-run warning threshold; 0 to disable
```

- **`layout = "flat"`** (default) — every artifact lands under
  `artifacts/<name>.<ext>`. Non-breaking with any existing notebook.
- **`layout = "by_notebook"`** — path-less figures and tables land under
  `artifacts/<notebook-stem>/<name>.<ext>`. Good when one project has
  many notebooks producing similarly-named outputs.
- **`layout = "by_cell"`** —
  `artifacts/<notebook-stem>/<cell-name>/<name>.<ext>`. Every artifact's
  path names its producer, which agents and human reviewers can read
  at a glance without opening the manifest.

The `max_committed_size_mb` threshold drives a post-run warning from
`jellycell run` when any single artifact exceeds the limit — pointing
at either `.gitignore` or Git LFS. See the [`large-data`](https://github.com/random-walks/jellycell/tree/main/examples/large-data)
example for the "commit the story, git-ignore the bulk" workflow.

### `[journal]`

Append-only per-run log written to `<manuscripts>/<path>` after every
`jellycell run`. Captures timestamp, notebook, cell summary, new
artifacts (with their captions, when present), any large-artifact
warnings, and the optional `-m "message"` note. Append-only from
jellycell's side so hand-edits survive future runs.

```toml
[journal]
enabled = true                    # default; set false to skip the trail
path = "journal.md"               # relative to paths.manuscripts
```

The journal is intentionally committed for real projects — it's the
analysis trajectory a reviewer (or you in six months) can scan to
understand "why did the numbers change between runs?" Set
`enabled = false` only when the project is truly transient.


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

## `manuscripts/` — hand-authored writeups + tearsheets

The `manuscripts/` directory holds markdown files that live alongside
notebooks. By convention it has a clean two-way split:

```
manuscripts/
├── README.md              # explains the layout (optional but helpful)
├── paper.md               # hand-authored; you own this
├── reviewer-memo.md       # hand-authored; you own this
└── tearsheets/            # auto-generated; regenerate overwrites
    ├── analysis.md        # = notebooks/analysis.py
    └── exploration.md     # = notebooks/exploration.py
```

- **Root `manuscripts/*.md`** — hand-authored writeups: paper drafts,
  thesis chapters, decision memos, reviewer notes. Stable across any
  tearsheet regeneration. You edit freely; nothing overwrites your work.
- **`manuscripts/tearsheets/*.md`** — produced by
  `jellycell export tearsheet <nb>`, which writes
  `manuscripts/tearsheets/<stem>.md` by default. Markdown narration +
  inlined figures (via `../../artifacts/foo.png` relative paths) + JSON
  summaries as two-column tables. Header links back to the source
  notebook and the rendered HTML report when it exists. Regenerating
  overwrites the file, so never hand-edit; use the `-o PATH` override
  to target somewhere else if you need custom layouts.

Both reference the same `artifacts/` tree, so figures in the hand-authored
paper and the tearsheet dashboard are always byte-identical to the latest
run. Commit `manuscripts/` so reviewers and agents see the latest
tearsheets + writeups without re-running anything.

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
