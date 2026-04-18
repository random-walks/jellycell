# minimal

The smallest possible jellycell project: one notebook, one cell, one `print`.

Useful for:

- Sanity-checking your install (`jellycell run notebooks/hello.py` should be
  green in under a second).
- Copy-pasting as a starting point for your own project.
- Seeing what gets committed vs. cached (`.jellycell/cache/` is git-ignored).

## Bootstrap

```bash
# Option A: uv (preferred)
uv sync                                                   # run from repo root
cd examples/minimal
uv run jellycell run notebooks/hello.py

# Option B: pip + venv
python -m venv .venv && source .venv/bin/activate
pip install jellycell                                     # CLI only
jellycell run notebooks/hello.py
```

Add the `[server]` extra (`pip install 'jellycell[server]'`) for the live
viewer; `[examples]` if you want numpy/pandas/matplotlib for the richer
sibling examples.

## Layout

```
minimal/
├── jellycell.toml                 # project config (defaults only)
├── notebooks/hello.py             # one cell, one print
├── manuscripts/
│   ├── README.md                  # describes the folder split
│   └── notes.md                   # hand-authored analyst reflection
└── artifacts/                     # nothing produced yet
```

The hand-authored notes file ([`manuscripts/notes.md`](manuscripts/notes.md))
shows the "write next to your code" pattern: plain markdown, committed
alongside the notebook. No tearsheet for this example — `minimal` has
nothing to summarize.

## What's next

Step up to [`../demo/`](../demo/) for a full `jc.*` API tour, or
[`../paper/`](../paper/) for the hand-authored-paper-alongside-tearsheet
workflow.
