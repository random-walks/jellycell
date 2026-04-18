# timeseries

Three notebooks chained through artifact-based dataflow — the textbook
jellycell pattern. Each notebook runs in its own subprocess kernel, so
there's no shared in-memory state; everything travels through
`artifacts/*.parquet` via `jc.load` / `jc.save`.

The [manuscripts folder](manuscripts/) holds a hand-authored
[`findings.md`](manuscripts/findings.md) analyst's read plus one
auto-generated tearsheet per notebook.

## Bootstrap

```bash
# uv (preferred — installs numpy/pandas/matplotlib/pyarrow via [examples])
uv sync
cd examples/timeseries
uv run jellycell run notebooks/01-explore.py -m "first pass: synthetic daily series"
uv run jellycell run notebooks/02-decompose.py -m "additive decomposition"
uv run jellycell run notebooks/03-forecast.py -m "SES forecast + diagnostics"
uv run jellycell render
uv run jellycell view                                # needs [server]

# pip
pip install 'jellycell[server,examples]'
for nb in notebooks/*.py; do jellycell run "$nb" -m "first pass"; done
jellycell render
jellycell view
```

## Pipeline

```
01-explore.py  ─ writes daily.parquet, summary.json, two plots
     │
     ▼
02-decompose.py ─ reads daily.parquet, writes decomposed.parquet + plot
     │
     ▼
03-forecast.py  ─ reads decomposed.parquet, writes forecast + diagnostics + report.json
```

Edit the noise seed in `01-explore.py::raw` and watch the downstream
cache invalidate all the way through — `jc.load` registers the dep edge
automatically via the artifact lineage index.

## What this example shows

- **Cross-notebook dataflow via artifacts** — no shared kernels, no
  hand-written DAG config. Each `jc.load` creates a dep edge.
- **Matplotlib figures** via `jc.figure(fig=fig)` — PNGs under
  `artifacts/` that the tearsheets embed with relative paths.
- **JSON digests flattened into tearsheet tables** — the
  `report.json` from `03-forecast.py` becomes a nested-key table with
  `in_sample.*` and `residuals.*` fields. Open
  [`manuscripts/tearsheets/03-forecast.md`](manuscripts/tearsheets/03-forecast.md)
  to see.
- **Synthetic data by design** — CI runs are reproducible without
  external downloads. Swap the `raw` cell for `pd.read_csv(...)` against
  real data and everything downstream works unchanged.

## Manuscripts

See [`manuscripts/README.md`](manuscripts/README.md) for the full index.
Highlights:

- [`manuscripts/findings.md`](manuscripts/findings.md) — hand-authored
  analyst's interpretation of seasonality, forecast quality, residual
  diagnostics.
- [`manuscripts/tearsheets/03-forecast.md`](manuscripts/tearsheets/03-forecast.md)
  — the auto-generated dashboard for the forecast notebook.
