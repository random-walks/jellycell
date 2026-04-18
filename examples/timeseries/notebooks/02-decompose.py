# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pandas", "matplotlib", "pyarrow"]
# ///

# %% [markdown]
# # Decompose — trend, seasonality, residuals
#
# Loads the Parquet artifact from `01-explore.py`, splits the series into
# three components using classical additive decomposition:
#
# \[ y_t = T_t + S_t + R_t \]
#
# where the trend `T` is a centered 7-day rolling mean, the seasonality `S` is
# the average detrended value by weekday, and the residual `R` is whatever's
# left. All three are persisted as artifacts.

# %% tags=["jc.load", "name=loaded"]
import pandas as pd

import jellycell.api as jc

df: pd.DataFrame = jc.load("artifacts/daily.parquet")
df = df.set_index("date")
print(df.head())

# %% tags=["jc.step", "name=trend", "deps=loaded"]
trend = df["value"].rolling(7, center=True).mean()
print(f"trend span: {trend.first_valid_index().date()} \u2013 {trend.last_valid_index().date()}")

# %% tags=["jc.step", "name=seasonality", "deps=trend"]
detrended = df["value"] - trend
by_dow = detrended.groupby(detrended.index.dayofweek).mean()
seasonality = pd.Series(by_dow.loc[df.index.dayofweek].values, index=df.index)
print("mean seasonal effect by weekday:")
print(
    pd.DataFrame(
        {"dow": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "effect": by_dow.round(2).values}
    ).to_string(index=False)
)

# %% tags=["jc.step", "name=residuals", "deps=trend", "deps=seasonality"]
residuals = df["value"] - trend - seasonality
print(f"residual std: {residuals.std():.3f}")
print(f"residual mean: {residuals.mean():.3f} (should be near 0)")

# %% tags=["jc.step", "name=persist", "deps=trend", "deps=seasonality", "deps=residuals"]
decomposed = pd.DataFrame(
    {
        "observed": df["value"],
        "trend": trend,
        "seasonal": seasonality,
        "residual": residuals,
    }
).reset_index()
jc.save(decomposed, "artifacts/decomposed.parquet")

# %% tags=["jc.figure", "name=decomp_plot", "deps=persist"]
import matplotlib.pyplot as plt

fig, axes = plt.subplots(4, 1, figsize=(10, 9), sharex=True)
plots = [
    ("observed", df["value"], "#1a1a1a"),
    ("trend", trend, "#4f46e5"),
    ("seasonal", seasonality, "#0891b2"),
    ("residual", residuals, "#dc2626"),
]
for ax, (label, series, color) in zip(axes, plots, strict=True):
    ax.plot(series.index, series.values, linewidth=1.1, color=color)
    ax.set_ylabel(label)
    ax.grid(alpha=0.3)
axes[0].set_title("Additive decomposition")
axes[-1].set_xlabel("Date")
fig.tight_layout()
jc.figure(path="artifacts/decomposition.png", fig=fig)
