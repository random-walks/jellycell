# demo

A tour of the `jc.*` API with zero external deps. Every notebook feature
you're likely to use in a real project is exercised: `jc.setup` configs,
`jc.load` round-trip, implicit dep registration, JSON summaries that
flow into the tearsheet.

## Bootstrap

```bash
# uv (preferred)
uv sync                                   # from repo root — no extras needed
cd examples/demo
uv run jellycell run notebooks/tour.py -m "first pass"
uv run jellycell export tearsheet notebooks/tour.py
uv run jellycell view                     # needs [server] extra

# pip
pip install 'jellycell[server]'
jellycell run notebooks/tour.py -m "first pass"
jellycell export tearsheet notebooks/tour.py
jellycell view
```

The `-m "..."` flag appends the message to `manuscripts/journal.md`
alongside cell counts + artifact changes — quick audit trail for "what
did I do?" a week from now.

```bash
# You can skip the message; default-on journal still records the run:
uv run jellycell run notebooks/tour.py
```

## Layout

```
demo/
├── jellycell.toml                         # flat artifact layout (default)
├── notebooks/tour.py                      # setup + load + step + save + load round-trip
├── artifacts/                             # small JSONs, committed
├── reports/                               # jellycell render output
└── manuscripts/
    ├── README.md
    ├── analysis.md                        # hand-authored interpretation of the run
    └── tearsheets/
        └── tour.md                        # auto-generated; regenerate overwrites
```

## What this example shows

- **`kind=setup`** cells — hyperparameter-like declarations that surface as
  source blocks in the tearsheet.
- **`jc.load` roundtrip** — the `roundtrip` cell loads what the `summary`
  cell wrote; jellycell records an implicit dep edge via the artifact
  lineage index, so editing `summary` invalidates `roundtrip` too, no
  hand-written `deps=` needed.
- **JSON → tearsheet table** — every `jc.save(dict, "...json")` becomes
  a two-column markdown table in the tearsheet.
- **Cache invalidation on source edit** — change `CONVERSIONS` in the
  setup cell and watch the next run re-execute only the affected subgraph.

## Manuscripts

- [`manuscripts/analysis.md`](manuscripts/analysis.md) — hand-authored
  analyst's read on the numbers. Safe from regeneration.
- [`manuscripts/tearsheets/tour.md`](manuscripts/tearsheets/tour.md) —
  auto-generated dashboard. Regenerating overwrites.
