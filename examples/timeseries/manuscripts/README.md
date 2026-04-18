# Daily time series — notebook tour

Three notebooks, one artifact-based dataflow.

| # | Notebook            | Produces                                         |
| - | ------------------- | ------------------------------------------------ |
| 1 | `01-explore.py`     | `daily.parquet`, `summary.json`, raw + weekday plots |
| 2 | `02-decompose.py`   | `decomposed.parquet`, decomposition plot         |
| 3 | `03-forecast.py`    | `forecast.parquet`, `report.json`, forecast + residual diagnostics |

## Run

```bash
cd examples/timeseries
jellycell run notebooks/01-explore.py
jellycell run notebooks/02-decompose.py
jellycell run notebooks/03-forecast.py
jellycell view            # browse the catalogue
```

## Things to notice

- **Artifact-based dataflow.** Notebook 02 loads `artifacts/daily.parquet`
  (written by 01) via `jc.load`. No shared kernel state required — each
  notebook runs in its own subprocess kernel.
- **Matplotlib figures.** `jc.figure(fig=fig)` persists figures as PNG
  under `artifacts/` and surfaces them on the rendered HTML page.
- **Declared deps propagate cache invalidation.** Changing the noise seed in
  cell `raw` of `01-explore.py` invalidates the downstream cache in
  `02-decompose.py` too (because the Parquet bytes change).
- **Residual diagnostics.** `03-forecast.py` checks the fit's quality with a
  histogram + lag-1 autocorrelation scatter — the basics you'd want before
  trusting a forecast.

## What's synthetic vs. what's real

The data is synthetic (generated inline) so the demo is reproducible without
external downloads. The pipeline is real — swap the `raw` cell for a
`pd.read_csv(...)` over your actual daily data and everything downstream
works unchanged.
