# Conversion funnel — analyst read

Hand-authored commentary for the [`tour.py`](../notebooks/tour.py) run.
Pairs with the auto-generated [tearsheet](tearsheets/tour.md) for the
raw figures.

## Headline

**38 conversions / 450 sessions ≈ 8.4%.** That's solidly in the
"interesting but not a smoking gun" band for a landing-page funnel.
Enough volume to take the signal seriously; not enough to claim
anything causally.

## What I notice

- The `conversion_rate` field matches the hand-check (38 / 450 =
  0.08444...). Good — the pipeline and this writeup agree.
- The `headline` cell renders the human-readable phrasing alongside the
  machine-readable digest. Keeping both in the tearsheet means the
  reviewer doesn't have to interpret raw numbers.
- The `roundtrip` cell exists purely to demonstrate that `jc.load`
  registers a dep edge; the tearsheet skips it (no artifacts worth
  rendering) so the reader only sees the interesting rows.

## Caveats

- The setup cell uses literal counts because this is a demo. In a real
  funnel you'd pull from `data/` and expose the date range as part of
  the headline so caching invalidates on data edits.
- No confidence interval on the rate. For a 450-sample proportion the
  Wald 95% CI is roughly ±2.5pp. If you're making a decision on this
  number, go grab `statsmodels.stats.proportion.proportion_confint`.

## Next steps if extending

1. Add a `jc.load("data/sessions.csv")` cell and drive the numbers from
   real data.
2. Add a `kind=figure` cell that plots conversions by source/medium.
3. Re-run `jellycell export tearsheet notebooks/tour.py` — the new
   figure drops into the tearsheet automatically.
