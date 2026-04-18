# manuscripts/

Two kinds of markdown files live here:

- **Auto-generated tearsheets** under [`tearsheets/`](tearsheets/) —
  produced by `jellycell export tearsheet notebooks/<name>.py`.
  Regenerating overwrites them, so never hand-edit.
- **Hand-authored writeups** at the root — drafts, reviewer notes, this
  README:
  - [`findings.md`](findings.md) — analyst's interpretation of
    seasonality, forecast quality, and residual diagnostics.
  - (And this README itself, which indexes the tearsheets below.)

## Tearsheets in this project

| # | Notebook                                          | Tearsheet                                                  | Produces                                       |
| - | ------------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------- |
| 1 | [`01-explore.py`](../notebooks/01-explore.py)     | [`tearsheets/01-explore.md`](tearsheets/01-explore.md)     | `daily.parquet`, `summary.json`, two plots     |
| 2 | [`02-decompose.py`](../notebooks/02-decompose.py) | [`tearsheets/02-decompose.md`](tearsheets/02-decompose.md) | `decomposed.parquet`, decomposition plot       |
| 3 | [`03-forecast.py`](../notebooks/03-forecast.py)   | [`tearsheets/03-forecast.md`](tearsheets/03-forecast.md)   | `forecast.parquet`, `report.json`, diagnostics |

## Things to notice in the tearsheets

- **Artifact-based dataflow.** Notebook 02 loads `artifacts/daily.parquet`
  (written by 01) via `jc.load`. No shared kernel state — each notebook
  runs in its own subprocess kernel.
- **Matplotlib figures.** `jc.figure(fig=fig)` persists figures as PNG
  under `artifacts/`; the tearsheet embeds them with relative paths so
  GitHub renders them inline.
- **Declared deps propagate cache invalidation.** Changing the noise seed
  in cell `raw` of `01-explore.py` invalidates the downstream cache in
  `02-decompose.py` too (the Parquet bytes change).
- **JSON summaries.** Cells that call `jc.save(dict, "artifacts/<name>.json")`
  become two-column tables — see [`tearsheets/03-forecast.md`](tearsheets/03-forecast.md)
  for an example with nested `in_sample.*` and `residuals.*` fields.

## Regenerate

```bash
cd examples/timeseries
jellycell run notebooks/01-explore.py   notebooks/02-decompose.py   notebooks/03-forecast.py
jellycell export tearsheet notebooks/01-explore.py
jellycell export tearsheet notebooks/02-decompose.py
jellycell export tearsheet notebooks/03-forecast.py
```

## What's synthetic vs. what's real

The data is synthetic (generated inline) so the demo is reproducible without
external downloads. The pipeline is real — swap the `raw` cell for
`pd.read_csv(...)` over your actual daily data and everything downstream
works unchanged.
