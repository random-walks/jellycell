# paper-2026 — analysis journal

Append-only run log written by `jellycell run`. Each section below is
one invocation: timestamp, notebook, cell-change summary, and any new
or updated artifacts. Safe to hand-edit for commentary — the next
`jellycell run` only appends at the bottom.

Disable via `[journal] enabled = false` in `jellycell.toml`.

This particular file is committed as a **demonstration** of the
trajectory-log pattern — three entries showing how a small iteration
(first exploration → catching an error → the fix) gets recorded
automatically. In a real project the entries pile up as you work, and
the journal becomes an honest chronicle of how the result was
reached.

## 2026-04-18T18:09:58+00:00 — `notebooks/analysis.py`

> **Status:** ok · 6 ran · 0 cached · 0 errored · 1388ms · _first pass: mortality by country + yoy_

**Artifacts:**
- `artifacts/country_totals.png` (16.8 KB) — Figure 1: cumulative mortality by country, 2020–2021
- `artifacts/yoy_change.png` (12.9 KB) — Figure 2: year-over-year change (2021 vs 2020), percent
- `artifacts/summary.json` (226 B) — Table 1: headline mortality stats
- `artifacts/totals.json` (65 B) — Table 2: per-country mortality totals (2020–2021)

> **Review note (hand-added):** yoy chart looks odd — DE sitting at +59% vs UK
> near-flat is plausible, but double-check the sign convention in the
> `yoy_change` cell. Reading the code: `(2021 - 2020) / 2020` — positive means
> 2021 rose. That's correct. Moving on.

## 2026-04-18T18:24:02+00:00 — `notebooks/analysis.py`

> **Status:** ok · 6 ran · 0 cached · 0 errored · 1402ms · _tweak captions + polish labels for submission_

**Artifacts:**
- `artifacts/country_totals.png` (16.8 KB) — Figure 1: cumulative mortality by country, 2020–2021
- `artifacts/yoy_change.png` (12.9 KB) — Figure 2: year-over-year change (2021 vs 2020), percent
- `artifacts/summary.json` (226 B) — Table 1: headline mortality stats
- `artifacts/totals.json` (65 B) — Table 2: per-country mortality totals (2020–2021)

> **Review note:** captions now tagged with Figure N / Table N so the paper's
> inline references line up. Notes pickle cleanly into the tearsheet subtitle
> so reviewers can hover to see the methodology without flipping to the
> paper. This is the run I'd submit.

## 2026-04-18T18:45:40+00:00 — `notebooks/analysis.py`

> **Status:** ok · 4 cached · 2 ran · 0 errored · 241ms · _rerun after updating data/sample.csv_

**Artifacts:**
- `artifacts/country_totals.png` (16.8 KB) — Figure 1: cumulative mortality by country, 2020–2021
- `artifacts/summary.json` (234 B) — Table 1: headline mortality stats

> **Review note:** only the raw → per_country_totals subgraph re-executed
> (mixed cache/re-run, see the "note" banner in the CLI output). The yoy
> chart was unaffected — expected, no 2020/2021 rows moved — and the
> tearsheet picked up the new totals automatically on next
> `jellycell export tearsheet`.
