# manuscripts/

Two kinds of markdown files live here:

- **Hand-authored writeups at the root** — things you own and edit.
  - [`analysis.md`](analysis.md) — analyst read on the conversion numbers.
- **Auto-generated tearsheets** under [`tearsheets/`](tearsheets/) —
  produced by `jellycell export tearsheet notebooks/<name>.py`.
  Regenerating overwrites, so never hand-edit.
  - [`tearsheets/tour.md`](tearsheets/tour.md) — [`notebooks/tour.py`](../notebooks/tour.py)

Both views share the same `artifacts/` tree, so the JSON tables in the
analysis and the tearsheet are always byte-identical to the latest run.
