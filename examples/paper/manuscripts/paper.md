# Mortality trends (paper draft)

A minimal manuscript that cites figures and tables produced by
`notebooks/analysis.py`. In a jellycell project, manuscripts sit
alongside notebooks and can reference rendered artifacts directly.

## Background

One-paragraph background.

## Methods

See [`notebooks/analysis.py`](../notebooks/analysis.py). The `jc.load`
cell reads `data/sample.csv`; the dep-graph ensures every downstream
cell invalidates when the input changes.

## Results

Per-country mortality totals are persisted to
[`artifacts/totals.json`](../artifacts/totals.json) by the notebook.

## Reproducibility

```bash
cd examples/paper
jellycell run notebooks/analysis.py
jellycell render
```

All cells are cached on the second run; change an input row and only
the affected subgraph re-executes.
