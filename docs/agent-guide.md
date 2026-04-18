# Agent guide

:::{important}
Spec §10.3 stability contract. Content here is what `jellycell prompt` emits.
Patch-version releases MUST NOT change this page. Minor-version releases can
update it; every change gets a CHANGELOG entry.
:::

## What jellycell is

**jellycell** is a reproducible-analysis notebook tool. You write `.py` files
in jupytext percent format with optional PEP-723 dependency blocks; jellycell
runs them via a subprocess Jupyter kernel, caches cell outputs by content hash,
and serves a live HTML catalogue.

Agents: run `jellycell prompt` at the start of any new jellycell project to
pull this guide into your context.

## Project layout

Every jellycell project has a `jellycell.toml` at the root and this canonical
directory layout (all paths configurable via `[paths]` in `jellycell.toml`):

```
my-project/
├── jellycell.toml       # project config
├── notebooks/           # .py source notebooks (jupytext percent format)
├── data/                # input data, read by jc.load
├── artifacts/           # writable output files (images, parquet, json, ...)
├── reports/             # rendered HTML output
├── manuscripts/         # narrative docs (optional)
└── .jellycell/
    └── cache/           # content-addressed cache (git-ignored)
```

## File format

A notebook is a single `.py` file in jupytext percent format:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas"]
# ///

# %% [markdown]
# # Analysis title

# %% tags=["jc.load", "name=raw"]
import pandas as pd
df = pd.read_csv("data/input.csv")

# %% tags=["jc.step", "name=summary", "deps=raw"]
summary = df.describe()
```

Rules:

- The **PEP-723 block** (if present) must be at the top of the file. A lint
  rule rejects mid-file blocks with a `--fix` that moves them.
- Cells are separated by `# %%` markers. Markdown cells use `# %% [markdown]`.
- Cell metadata (especially `tags=[...]`) goes in the marker line.
- The file is valid Python — `uv run --script notebook.py` works.

## Cell tags

Tags live in the `tags=[...]` list on the cell marker:

| Tag          | Meaning                                       | Extra attrs          |
| ------------ | --------------------------------------------- | -------------------- |
| `jc.load`    | Loads input data (conventionally from `data/`) | `name=`              |
| `jc.step`    | Default — transform or compute                | `name=`, `deps=a,b`  |
| `jc.figure`  | Writes an image artifact                      | `name=`              |
| `jc.table`   | Writes a tabular artifact                     | `name=`              |
| `jc.setup`   | No deps; not cached; runs first               | —                    |
| `jc.note`    | Markdown-only; not executable                 | —                    |

`deps=a,b` declares that this cell depends on cells named `a` and `b`. The
cache key incorporates dep cells' hashes so invalidation propagates correctly.

Untagged code cells default to `jc.step` with an auto-generated name like
`<notebook>:<ordinal>`.

## The `jc.*` API

What you import inside a notebook cell:

```python
import jellycell.api as jc

# writes
jc.save(obj, "artifacts/summary.json")        # format inferred from suffix
jc.save(df, "artifacts/data.parquet")
jc.figure("artifacts/plot.png", fig=plt.gcf())
jc.table(df, name="results")

# reads (registers a dep edge on the producing cell when inside a run)
jc.load("artifacts/summary.json")

# explicit deps — AST-walked statically, so they enter the cache key
# before the cell runs (the runner parses jc.deps(...) out of cell source).
jc.deps("raw", "processed")

# function-level memoization — uses the same CacheStore as cells.
@jc.cache
def expensive(x, y):
    return heavy_compute(x, y)

# cache context (read-only)
jc.ctx.notebook      # "notebooks/foo.py"
jc.ctx.cell_id       # "foo:3"
jc.ctx.cell_name     # "summary" or None
jc.ctx.project       # the jellycell.paths.Project
jc.ctx.inside_run    # True inside `jellycell run`; False standalone
```

All `jc.*` calls work standalone (plain file ops) OR inside `jellycell run`
(path resolution relative to the project root; artifacts tracked in the
cell's manifest).

Supported `jc.save` formats: `.parquet`, `.csv`, `.json`, `.pkl`, `.png`.

## CLI commands

| Command                            | Purpose                                          |
| ---------------------------------- | ------------------------------------------------ |
| `jellycell init <path>`            | Scaffold a new project                           |
| `jellycell lint [path] [--fix]`    | Run lint rules; auto-fix where possible          |
| `jellycell run <notebook>`         | Execute a notebook (cached cells skipped)        |
| `jellycell render [notebook]`      | Render HTML to `reports/`                        |
| `jellycell view`                   | Serve live catalogue (requires `[server]` extra) |
| `jellycell cache list`             | List cached cell executions                      |
| `jellycell cache prune`            | Remove old entries (`--older-than`, `--keep-last`) |
| `jellycell cache clear`            | Wipe the cache                                   |
| `jellycell cache rebuild-index`    | Rebuild SQLite index from manifests              |
| `jellycell export ipynb <nb>`      | Export to `.ipynb` with cached outputs           |
| `jellycell export md <nb>`         | Export to MyST markdown (full notebook + outputs) |
| `jellycell export tearsheet <nb>`  | Curated markdown tearsheet → `manuscripts/tearsheets/<stem>.md` |
| `jellycell new <name>`             | Scaffold a new notebook                          |
| `jellycell prompt`                 | Emit this guide to stdout                        |

Every command supports `--json` for machine-readable output with
`schema_version: 1`.

## Idiomatic patterns

- **Name every cell** (`name=foo`). Named cells are referenceable from
  `deps=...`, discoverable in manifests, and easier to re-run selectively.
- **Declare deps explicitly**. Running `jellycell lint` with
  `enforce_declared_deps = true` catches undeclared implicit deps.
- **Write artifacts under `artifacts/`**, not inline to the notebook's
  directory. The `enforce_artifact_paths` rule catches mistakes.
- **Inter-cell data goes through `jc.save`/`jc.load`.** Cells that are
  cached don't re-execute — their in-memory variables aren't available to
  re-executed dependent cells. The `jellycell run` CLI warns when a run
  mixes cache hits and re-executions.
- **Commit a lockfile for reproducibility.** `env_hash` prefers
  `uv.lock` / `poetry.lock` bytes over the PEP-723 `dependencies` list, so
  two environments with matching dep names but different resolved versions
  don't silently share caches.
- **Keep cells small**. One logical operation per cell means the cache is
  granular. Change one summary → only the summary re-runs.
- **PEP-723 `[tool.jellycell]` overrides** apply at file scope. Supported
  keys: `project.name`, `run.kernel`, `run.timeout_seconds`. Unknown keys
  raise a lint error (no silent typos).
- **Don't mock the cache**. If tests need the cache, use a real
  `CacheStore` against `tmp_path`.
- **Share results via tearsheets.** `jellycell export tearsheet <nb>`
  writes a curated markdown file to `manuscripts/tearsheets/<stem>.md`:
  prose from markdown cells, inlined figures via relative paths, JSON
  summaries flattened to two-column tables. The `tearsheets/` subfolder
  convention keeps auto-generated files separate from hand-authored
  writeups (paper drafts, memos, thesis chapters) that live at the root
  of `manuscripts/`. GitHub renders the result inline — no HTML preview
  service needed; commit it alongside the notebook so reviewers see the
  latest run without cloning.
- **Pick an artifact layout that matches the project.** `[artifacts]
  layout` in `jellycell.toml` controls where path-less `jc.figure()` /
  `jc.table()` writes: `"flat"` (default), `"by_notebook"` →
  `artifacts/<notebook>/<name>.<ext>`, or `"by_cell"` →
  `artifacts/<notebook>/<cell>/<name>.<ext>`. `"by_cell"` makes every
  artifact self-identifying — handy for agents that need to trace
  "which cell produced this file?" without opening manifests.
- **Commit the story, git-ignore the bulk.** For datasets too big to
  commit, set `[artifacts] max_committed_size_mb` and let `jellycell
  run` warn you when an artifact crosses the line. Commit a tiny
  `headline.json` summary instead, git-ignore (or Git-LFS) the bytes,
  and reviewers regenerate from the seed + notebook locally. See
  `examples/large-data/` for the full pattern.

## Invariants (§10 contracts)

Three contracts, stable across patch releases. Living statement +
ceremony in [reference/contracts](reference/contracts.md):

1. **§10.1 `--json` schemas** carry `schema_version: 1`. Additive
   fields (optional + default) are patch- or minor-safe; renames,
   removals, and type changes force a major bump.
2. **§10.2 Cache key algorithm** (`jellycell.cache.hashing`) is frozen
   unless `MINOR_VERSION` in `_version.py` is bumped — which forces
   every cache to invalidate cleanly and rides a major release.
3. **§10.3 Agent guide content** (what `jellycell prompt` emits).
   Typo / clarification edits ride a patch; additive sections ride a
   minor; rewrites that change existing guidance force a major.
