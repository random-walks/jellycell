# jellycell examples

Runnable demonstration projects. Each directory is a self-contained
jellycell project with its own `README.md` (bootstrap + what it shows),
notebooks, artifacts, and manuscripts (hand-authored + auto-generated
tearsheets). Click through to any:

| Example                                | Shows                                                                                          |
| -------------------------------------- | ---------------------------------------------------------------------------------------------- |
| [minimal](minimal/README.md)           | Smallest possible project — one cell, one print.                                               |
| [demo](demo/README.md)                 | `jc.*` API tour: `kind=setup` cell, `jc.load` round-trip, implicit dep via load, JSON tearsheet tables. |
| [paper](paper/README.md)               | Research paper workflow: two matplotlib figures, hand-authored [`paper.md`](paper/manuscripts/paper.md) alongside the auto-generated [tearsheet](paper/manuscripts/tearsheets/analysis.md). PEP-723 `[tool.jellycell] timeout_seconds` override. |
| [ml-experiment](ml-experiment/README.md) | Training loop with loss curve + metrics JSON, tagged `kind=setup` hyperparams, hand-authored [`model-card.md`](ml-experiment/manuscripts/model-card.md).   |
| [timeseries](timeseries/README.md)     | Multi-notebook artifact dataflow: three notebooks chained via `jc.load` on Parquet; tearsheet per notebook + hand-authored [`findings.md`](timeseries/manuscripts/findings.md). |
| [large-data](large-data/README.md)     | Commit-the-story, git-ignore-the-bulk pattern: `[artifacts] layout = "by_notebook"`, `max_committed_size_mb` warning, reproducible seed, hand-authored [`data-notes.md`](large-data/manuscripts/data-notes.md). |

## Bootstrap cheatsheet

```bash
# uv — recommended; single `sync` pulls all extras
uv sync
cd examples/<name>
uv run jellycell run notebooks/<script>.py
uv run jellycell export tearsheet notebooks/<script>.py
uv run jellycell view                                 # needs [server]

# pip — pick the extras you want
pip install 'jellycell[server,examples]'              # matplotlib + pandas + pyarrow
cd examples/<name>
jellycell run notebooks/<script>.py
jellycell export tearsheet notebooks/<script>.py
jellycell view
```

Per-example READMEs spell out the exact commands for each project.

## The `manuscripts/` split

By convention, each example's `manuscripts/` folder has two kinds of
markdown:

- **Root `manuscripts/*.md`** — hand-authored writeups (paper drafts,
  thesis chapters, reviewer memos, model cards, analyst findings).
  Stable across regeneration. Durable prose.
- **`manuscripts/tearsheets/*.md`** — auto-generated via
  `jellycell export tearsheet <nb>` (default output). Markdown
  narration + inlined figures + JSON digests as two-column tables.
  Regenerating overwrites — never hand-edit.

Browse a few:

- [`paper/manuscripts/paper.md`](paper/manuscripts/paper.md) — durable
  research writeup.
- [`paper/manuscripts/tearsheets/analysis.md`](paper/manuscripts/tearsheets/analysis.md)
  — same run, auto-generated dashboard.
- [`timeseries/manuscripts/findings.md`](timeseries/manuscripts/findings.md)
  — analyst interpretation.
- [`timeseries/manuscripts/tearsheets/03-forecast.md`](timeseries/manuscripts/tearsheets/03-forecast.md)
  — plots + nested-JSON tables.

## Artifact organization

Each example configures `[artifacts]` in its `jellycell.toml` to match
its shape. Options:

- `layout = "flat"` (default) — all artifacts under `artifacts/`. Simplest.
- `layout = "by_notebook"` — bucketed under `artifacts/<notebook-stem>/`.
  Scales well when a project has many notebooks producing similar names.
- `layout = "by_cell"` — `artifacts/<notebook-stem>/<cell-name>/<name>.<ext>`.
  Agent-friendly: every file's path names its producer.

Explicit paths in `jc.save(x, "artifacts/custom.json")` always win —
the layout setting only affects path-less `jc.figure()` / `jc.table()`
calls where jellycell picks the location.

## Oversized artifacts

Projects with big outputs set `[artifacts] max_committed_size_mb = N`
(default `50`). After `jellycell run`, any artifact over the threshold
gets a warning with `.gitignore` / LFS guidance. The
[`large-data/`](large-data/) example demonstrates the full workflow.
