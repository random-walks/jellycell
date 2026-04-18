# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pandas", "matplotlib", "pyarrow"]
# ///

# %% [markdown]
# # Explore — daily time series
#
# A self-contained tour of:
#
# - Generating a synthetic daily series with trend + weekly seasonality + noise.
# - Running summary statistics.
# - Plotting raw values vs. a 7-day rolling mean.
# - Persisting cleaned data as a Parquet artifact for downstream notebooks.

# %% tags=["jc.load", "name=raw"]
import numpy as np
import pandas as pd

rng = np.random.default_rng(seed=42)

dates = pd.date_range("2025-01-01", periods=365, freq="D")
trend = np.linspace(100, 120, len(dates))  # slow upward drift
weekly = np.where(
    dates.dayofweek >= 5,  # Sat, Sun
    5.0,
    np.where(dates.dayofweek == 0, -2.0, 0.0),  # Mon dips
)
noise = rng.normal(0.0, 3.0, len(dates))
value = trend + weekly + noise

df = pd.DataFrame({"date": dates, "value": value})
print(f"rows: {len(df)}   range: {df['value'].min():.2f} \u2013 {df['value'].max():.2f}")
df.head()

# %% tags=["jc.step", "name=summary", "deps=raw"]
import jellycell.api as jc

summary = {
    "rows": len(df),
    "mean": round(float(df["value"].mean()), 3),
    "std": round(float(df["value"].std()), 3),
    "min": round(float(df["value"].min()), 3),
    "max": round(float(df["value"].max()), 3),
    "start": df["date"].min().date().isoformat(),
    "end": df["date"].max().date().isoformat(),
}
jc.save(summary, "artifacts/summary.json")
jc.save(df, "artifacts/daily.parquet")
print(summary)

# %% tags=["jc.figure", "name=raw_plot", "deps=raw"]
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(df["date"], df["value"], linewidth=0.9, color="#6b7280", label="daily")
ax.plot(
    df["date"],
    df["value"].rolling(7, center=True).mean(),
    linewidth=2.0,
    color="#4f46e5",
    label="7-day rolling mean",
)
ax.set_title("Daily series: raw vs. 7-day moving average")
ax.set_xlabel("Date")
ax.set_ylabel("Value")
ax.legend(loc="lower right", frameon=False)
ax.grid(alpha=0.3)
fig.autofmt_xdate()
jc.figure(path="artifacts/raw_plot.png", fig=fig)

# %% tags=["jc.figure", "name=weekday_profile", "deps=raw"]
# Weekday-of-week profile: box-plot residuals after de-trending.
detrended = df["value"] - df["value"].rolling(7, center=True).mean()
df_plot = pd.DataFrame({"dow": df["date"].dt.day_name(), "residual": detrended})
order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

fig, ax = plt.subplots(figsize=(8, 4))
box = [df_plot.loc[df_plot["dow"] == d, "residual"].dropna().values for d in order]
ax.boxplot(
    box,
    labels=[d[:3] for d in order],
    patch_artist=True,
    boxprops={"facecolor": "#eef2ff", "edgecolor": "#4f46e5"},
    medianprops={"color": "#4f46e5", "linewidth": 1.5},
)
ax.axhline(0, color="#6b7280", linewidth=0.8, linestyle="--")
ax.set_title("Weekly seasonality (detrended residuals by weekday)")
ax.set_ylabel("Residual")
ax.grid(alpha=0.3, axis="y")
jc.figure(path="artifacts/weekday_profile.png", fig=fig)
