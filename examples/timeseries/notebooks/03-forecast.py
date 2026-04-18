# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pandas", "matplotlib", "pyarrow"]
# ///

# %% [markdown]
# # Forecast — exponential smoothing + diagnostics
#
# Loads the decomposition, fits a simple exponential smoothing (level-only)
# with $\alpha = 0.3$, projects 30 days ahead, and checks residual whiteness
# via a histogram + lag-1 autocorrelation.

# %% tags=["jc.load", "name=loaded"]
import numpy as np
import pandas as pd

import jellycell.api as jc

decomposed: pd.DataFrame = jc.load("artifacts/decomposed.parquet")
decomposed = decomposed.set_index("date")
print(f"loaded {len(decomposed)} rows, cols: {list(decomposed.columns)}")

# %% tags=["jc.step", "name=ses_fit", "deps=loaded"]
ALPHA = 0.30
y = decomposed["observed"].to_numpy()
level = np.zeros_like(y)
level[0] = y[0]
for t in range(1, len(y)):
    level[t] = ALPHA * y[t] + (1 - ALPHA) * level[t - 1]

in_sample = pd.Series(level, index=decomposed.index, name="level")
residuals = decomposed["observed"] - in_sample
mae = float(residuals.abs().mean())
rmse = float(np.sqrt((residuals**2).mean()))
print(f"alpha={ALPHA}  MAE={mae:.3f}  RMSE={rmse:.3f}")

# %% tags=["jc.step", "name=forecast", "deps=ses_fit"]
HORIZON = 30
seasonality = decomposed["seasonal"]
# Level-only SES projects a flat line; blend weekly seasonality back in.
last_level = float(level[-1])
future_idx = pd.date_range(decomposed.index[-1] + pd.Timedelta(days=1), periods=HORIZON, freq="D")
# Re-use the fitted weekday effects.
dow_effect = seasonality.groupby(seasonality.index.dayofweek).mean()
future_season = dow_effect.loc[future_idx.dayofweek].values
forecast = pd.Series(last_level + future_season, index=future_idx, name="forecast")

# Conservative \u00b1 2*\u03c3 band around residual noise.
sigma = float(residuals.std())
band = 2.0 * sigma
forecast_df = pd.DataFrame(
    {
        "forecast": forecast,
        "upper": forecast + band,
        "lower": forecast - band,
    }
).reset_index(names="date")
jc.save(forecast_df, "artifacts/forecast.parquet")
print(forecast_df.head())

# %% tags=["jc.figure", "name=forecast_plot", "deps=forecast"]
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 4.5))
ax.plot(decomposed.index, decomposed["observed"], linewidth=0.9, color="#6b7280", label="observed")
ax.plot(in_sample.index, in_sample.values, linewidth=1.5, color="#4f46e5", label=f"SES α={ALPHA}")
ax.plot(forecast.index, forecast.values, linewidth=2.0, color="#dc2626", label="forecast")
ax.fill_between(
    forecast.index,
    forecast.values - band,
    forecast.values + band,
    color="#dc2626",
    alpha=0.15,
    label="±2σ band",
)
ax.axvline(decomposed.index[-1], color="#6b7280", linestyle="--", linewidth=0.8)
ax.set_title("Exponential smoothing with 30-day forecast")
ax.set_xlabel("Date")
ax.set_ylabel("Value")
ax.legend(loc="upper left", frameon=False)
ax.grid(alpha=0.3)
fig.autofmt_xdate()
jc.figure(path="artifacts/forecast_plot.png", fig=fig)

# %% tags=["jc.figure", "name=residual_diag", "deps=ses_fit"]
# Residual diagnostics: histogram + lag-1 autocorrelation.
lag1 = float(residuals.autocorr(1))

fig, (hax, sax) = plt.subplots(1, 2, figsize=(10, 4))
hax.hist(residuals.dropna(), bins=30, color="#4f46e5", alpha=0.75, edgecolor="#1a1a1a")
hax.axvline(0, color="#6b7280", linewidth=0.8, linestyle="--")
hax.set_title(f"Residual distribution (μ={residuals.mean():.2f}, σ={residuals.std():.2f})")
hax.set_xlabel("Residual")
hax.grid(alpha=0.3)

sax.scatter(residuals[:-1], residuals[1:], s=8, alpha=0.5, color="#0891b2")
sax.axhline(0, color="#6b7280", linewidth=0.8, linestyle="--")
sax.axvline(0, color="#6b7280", linewidth=0.8, linestyle="--")
sax.set_title(f"Residual lag-1 scatter (ρ₁={lag1:.3f})")
sax.set_xlabel("resid(t)")
sax.set_ylabel("resid(t+1)")
sax.grid(alpha=0.3)

fig.tight_layout()
jc.figure(path="artifacts/residuals.png", fig=fig)

# %% tags=["jc.step", "name=report", "deps=forecast", "deps=residual_diag"]
report = {
    "alpha": ALPHA,
    "in_sample": {"mae": round(mae, 3), "rmse": round(rmse, 3)},
    "residuals": {
        "mean": round(float(residuals.mean()), 3),
        "std": round(float(residuals.std()), 3),
        "lag1": round(lag1, 3),
    },
    "forecast_horizon_days": HORIZON,
    "forecast_range": {
        "first": forecast_df["date"].min().date().isoformat(),
        "last": forecast_df["date"].max().date().isoformat(),
    },
}
jc.save(report, "artifacts/report.json")
print(report)
