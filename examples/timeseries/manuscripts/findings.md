# Timeseries findings — analyst notes

Hand-authored interpretation of the three-notebook pipeline. Pairs with
the auto-generated [tearsheets](tearsheets/) — this file is the
"so what?" layer that the dashboard can't give you.

## Summary

The synthetic daily series shows a clean linear trend (~100 → 120
across the year) on top of a mild weekly seasonality (weekend lifts,
Monday dips) with homoscedastic noise. An α=0.3 exponential smoothing
with the weekly seasonal effect blended back in produces a 30-day
forecast whose residuals look roughly uncorrelated and roughly
zero-centered — see [`tearsheets/03-forecast.md`](tearsheets/03-forecast.md).

## Findings

### 1. The weekly seasonality is real and clean

From [`01-explore.py`](../notebooks/01-explore.py)'s weekday profile:

- Weekends (Sat/Sun) run ~5 units above the detrended mean.
- Monday runs ~2 units below.
- Tue–Fri are flat within noise.

This matches the synthetic data generator (intended), but the point
generalises: decompose before you forecast, and you get a chart that
tells you whether there's weekly structure at all.

### 2. The trend is linear within the sample

02-decompose extracts a centered 7-day rolling mean as trend. Visually
it's a straight line across the year with a handful of 1–2 unit
deviations — fine for a naïve level-only SES forecast at this horizon.

If the trend looked non-linear (curvy / S-shaped / piecewise), we'd
want a Holt-style forecast that models the slope, not just the level.

### 3. Forecast quality: acceptable, not great

From `report.json` (see the tearsheet):

- **MAE ≈ 2.25**, **RMSE ≈ 2.86**. Against a series with std ≈ 7,
  that's ~30–40% of one standard deviation — meaningful but not tight.
- **Residual lag-1 autocorrelation ≈ 0.01**. Essentially zero — the
  model isn't leaving predictable structure on the table.
- **Residual mean ≈ 0.12**. A whiff of positive bias but well below
  half a std. Not worth fixing at this data size.

### 4. What I'd change for a real deployment

- Replace level-only SES with Holt (level + slope) to track the trend
  properly.
- Widen the ±2σ forecast band to a proper bootstrap interval if you
  need calibrated tail behavior.
- Hold out the last 30 days of real data for an honest
  out-of-sample MAE before trusting the forecast range reported here.

## Reproducibility

Every figure and number in this memo traces back to a cache key. Re-run:

```bash
cd examples/timeseries
jellycell run notebooks/01-explore.py
jellycell run notebooks/02-decompose.py
jellycell run notebooks/03-forecast.py
```

The noise seed (`np.random.default_rng(seed=42)` in `01-explore.py`)
makes the synthetic series deterministic. Change the seed and the
subgraph — including this note's headline numbers — invalidates.

## Links

- Notebooks: [`../notebooks/`](../notebooks/)
- Tearsheets: [`tearsheets/`](tearsheets/)
- HTML reports: `site/*.html` after `jellycell render`.
