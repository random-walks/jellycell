# manuscripts/

Two kinds of markdown files live here. The split is the convention
`jellycell export tearsheet` follows by default:

- **Hand-authored writeups at the root** — the durable prose. Edit these
  freely; nothing will overwrite them. In this example:
  - [`paper.md`](paper.md) — the paper draft that cites the figures.
- **Auto-generated tearsheets under [`tearsheets/`](tearsheets/)** — a
  curated dashboard of figures + summary tables. Regenerating any
  tearsheet with `jellycell export tearsheet notebooks/<name>.py`
  overwrites the file, so never hand-edit these.
  - [`tearsheets/analysis.md`](tearsheets/analysis.md) — [`notebooks/analysis.py`](../notebooks/analysis.py)

The two views share the same `artifacts/` tree, so the figures in the
paper and the tearsheet are always byte-identical to the latest run.
