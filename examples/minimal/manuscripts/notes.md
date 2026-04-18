# First-run notes

A scratchpad that walks through the tiniest jellycell loop. Re-run
`jellycell run notebooks/hello.py` twice and watch the cache kick in.

## What happened the first time

The one code cell printed `hello from jellycell` and jellycell persisted
a manifest under `.jellycell/cache/manifests/`. Nothing under
`artifacts/` — the cell didn't call `jc.save`, so no outputs to commit.

## What happened the second time

`jellycell run notebooks/hello.py` reported `1 cached`. The cell's
normalized source didn't change, the (empty) PEP-723 dependency list
didn't change, so the cache-key matched and the cell was skipped.

## What I'd change if this were a real project

- Add a real input under `data/` and read it via `jc.load`.
- Save a summary as `artifacts/greeting_summary.json` via `jc.save` so
  downstream steps can `jc.load` it and the lineage index picks up the
  dep edge automatically.
- Generate a tearsheet with `jellycell export tearsheet notebooks/hello.py`
  — for a one-cell notebook it won't tell you much, but with five or six
  cells producing figures, it becomes the fastest way to share results.

## Links

- Notebook: [`../notebooks/hello.py`](../notebooks/hello.py)
- Run command: `jellycell run notebooks/hello.py`
- Top-level README: [`../README.md`](../README.md)
