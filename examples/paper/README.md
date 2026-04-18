# paper

A research-paper workflow: the notebook ([`analysis.py`](notebooks/analysis.py))
produces the numbers and figures; the hand-authored paper
([`paper.md`](manuscripts/paper.md)) cites them. A tearsheet
([`tearsheets/analysis.md`](manuscripts/tearsheets/analysis.md)) is
regenerated on every run as a dashboard-style companion.

The paper + tearsheet split is the core pattern:

- **`manuscripts/paper.md`** — the durable narrative. Edit freely.
- **`manuscripts/tearsheets/analysis.md`** — auto-generated; overwritten on
  regenerate.

## Bootstrap

```bash
# uv (preferred)
uv sync                                              # all-extras for matplotlib
cd examples/paper
uv run jellycell run notebooks/analysis.py
uv run jellycell export tearsheet notebooks/analysis.py
uv run jellycell render                              # HTML catalogue
uv run jellycell view                                # needs [server]

# pip
pip install 'jellycell[server,examples]'             # matplotlib via [examples]
jellycell run notebooks/analysis.py
jellycell export tearsheet notebooks/analysis.py
jellycell render
jellycell view
```

## What this example shows

- **PEP-723 `[tool.jellycell]` override** — the notebook sets
  `timeout_seconds = 180` inline, so the run-wide default is overridden
  just for this file.
- **Two `jc.figure` cells** — `country_totals` and `yoy_change` —
  persisted as PNGs and referenced by both `paper.md` and the tearsheet.
- **Hand-authored paper + auto tearsheet, sharing artifacts** — same
  `artifacts/` tree feeds both views. Figures stay in sync across every
  re-run.

## Layout

```
paper/
├── jellycell.toml
├── notebooks/analysis.py
├── data/sample.csv                         # tiny input (committed)
├── artifacts/                              # figures + summary JSON
├── reports/analysis.html                   # HTML report (committed)
└── manuscripts/
    ├── README.md
    ├── paper.md                            # hand-authored paper draft
    └── tearsheets/
        └── analysis.md                     # auto-generated dashboard
```

## Manuscripts

- [`manuscripts/paper.md`](manuscripts/paper.md) — the paper draft
  (background, methods, results, reproducibility).
- [`manuscripts/tearsheets/analysis.md`](manuscripts/tearsheets/analysis.md)
  — the auto-generated one-pager of the same run.
