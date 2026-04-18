# jellycell examples

Runnable demonstration projects. Enter any directory and run:

```bash
jellycell run notebooks/<name>.py
jellycell view                         # requires [server] extra
```

| Example                              | Shows                                                                                          |
| ------------------------------------ | ---------------------------------------------------------------------------------------------- |
| [minimal](minimal/)                  | Smallest possible project — one cell, one print.                                               |
| [demo](demo/)                        | `jc.*` API tour: `jc.load` round-trip, `kind=setup` cells, implicit dep via load, JSON tearsheet. |
| [paper](paper/)                      | Research paper workflow: two figures, per-country bar chart, year-over-year, hand-authored [`paper.md`](paper/manuscripts/paper.md) alongside the auto-generated [`tearsheet.md`](paper/manuscripts/tearsheet.md). PEP-723 `[tool.jellycell] timeout_seconds` override. |
| [ml-experiment](ml-experiment/)      | Tiny regression training loop with loss curve + metrics JSON, tagged `kind=setup` hyperparams. |
| [timeseries](timeseries/)            | Multi-notebook artifact dataflow: three notebooks chained via `jc.load` on Parquet, decomposition + forecast + diagnostics, one tearsheet per notebook. |

## Tearsheets

Each non-minimal example ships a committed `manuscripts/*.md` file — a
curated, markdown-native view of the notebook that GitHub renders inline
(no HTML, no external preview service). Browse a few:

- [`demo/manuscripts/tour.md`](demo/manuscripts/tour.md) — small, shows how setup cells and JSON summaries render.
- [`paper/manuscripts/tearsheet.md`](paper/manuscripts/tearsheet.md) — two bar charts + summary table.
- [`ml-experiment/manuscripts/train.md`](ml-experiment/manuscripts/train.md) — training curve + final metrics.
- [`timeseries/manuscripts/03-forecast.md`](timeseries/manuscripts/03-forecast.md) — two plots + nested JSON flattened to a two-column table.

Generate your own with:

```bash
jellycell export tearsheet notebooks/<name>.py
# → manuscripts/<name>.md
```

Hand-edit after if you want more narrative; re-running the command will
overwrite the file, so keep the hand-edited version at a different path
(like `manuscripts/paper.md` in the paper example).
