# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib"]
#
# [tool.jellycell]
# timeout_seconds = 180
# ///

# %% [markdown]
# # Mortality trend analysis
#
# A paper-shaped jellycell project: compute goes here, narrative lives in
# `manuscripts/paper.md`, figures are saved under `artifacts/` and linked
# from both the paper and the auto-generated tearsheet.

# %% tags=["jc.load", "name=raw"]
import csv
from pathlib import Path

with Path("data/sample.csv").open() as f:
    rows = list(csv.DictReader(f))
for row in rows:
    row["deaths"] = int(row["deaths"])
    row["year"] = int(row["year"])
print(f"loaded {len(rows)} rows across {len({r['country'] for r in rows})} countries")

# %% tags=["jc.step", "name=per_country_totals", "deps=raw"]
totals: dict[str, int] = {}
for row in rows:
    totals[row["country"]] = totals.get(row["country"], 0) + row["deaths"]
ranked = sorted(totals.items(), key=lambda kv: -kv[1])
for country, total in ranked:
    print(f"{country}: {total:,}")

# %% tags=["jc.step", "name=yoy_change", "deps=raw"]
# Year-over-year percent change per country, where both years are present.
by_country_year: dict[str, dict[int, int]] = {}
for row in rows:
    by_country_year.setdefault(row["country"], {})[row["year"]] = row["deaths"]
yoy: dict[str, float] = {}
for country, years in by_country_year.items():
    if 2020 in years and 2021 in years and years[2020] > 0:
        yoy[country] = (years[2021] - years[2020]) / years[2020]
for country, pct in sorted(yoy.items(), key=lambda kv: -kv[1]):
    print(f"{country}: {pct:+.1%}")

# %% tags=["jc.figure", "name=country_totals", "deps=per_country_totals"]
import matplotlib.pyplot as plt

import jellycell.api as jc

countries = [c for c, _ in ranked]
values = [t for _, t in ranked]
fig, ax = plt.subplots(figsize=(7, 3.2))
bars = ax.bar(countries, values, color="#4f46e5")
ax.set_ylabel("Total deaths (2020–2021)")
ax.set_title("Cumulative mortality by country")
ax.grid(alpha=0.3, axis="y")
ax.bar_label(bars, fmt="{:,.0f}", padding=3, fontsize=9)
fig.tight_layout()
jc.figure(
    path="artifacts/country_totals.png",
    fig=fig,
    caption="Figure 1: cumulative mortality by country, 2020–2021",
    notes=(
        "Bars sum deaths across both years. US dominates at ~74% of the "
        "four-country total; JP has the smallest absolute burden."
    ),
    tags=["result", "figure"],
)

# %% tags=["jc.figure", "name=yoy_chart", "deps=yoy_change"]
order = sorted(yoy.items(), key=lambda kv: -kv[1])
labels = [c for c, _ in order]
pcts = [v * 100 for _, v in order]
colors = ["#dc2626" if p > 0 else "#0891b2" for p in pcts]
fig, ax = plt.subplots(figsize=(7, 3.2))
ax.bar(labels, pcts, color=colors)
ax.axhline(0, color="#6b7280", linewidth=0.8)
ax.set_ylabel("2021 vs 2020 (%)")
ax.set_title("Year-over-year change in mortality")
ax.grid(alpha=0.3, axis="y")
fig.tight_layout()
jc.figure(
    path="artifacts/yoy_change.png",
    fig=fig,
    caption="Figure 2: year-over-year change (2021 vs 2020), percent",
    notes=(
        "Red bars = increase vs 2020, blue = decrease. DE stands out with "
        "a ~59% rise; UK is nearly flat."
    ),
    tags=["result", "figure"],
)

# %% tags=["jc.step", "name=summary", "deps=per_country_totals", "deps=yoy_change"]
summary = {
    "countries": len(totals),
    "years_covered": sorted({r["year"] for r in rows}),
    "top_country": ranked[0][0],
    "top_country_total": ranked[0][1],
    "combined_total": sum(totals.values()),
    "largest_yoy_increase_country": max(yoy, key=yoy.get),
    "largest_yoy_increase_pct": round(max(yoy.values()), 4),
}
jc.save(
    summary,
    "artifacts/summary.json",
    caption="Table 1: headline mortality stats",
    notes="One-number-per-concept digest; fits in the tearsheet as a 2-col table.",
    tags=["result", "table"],
)
jc.save(
    totals,
    "artifacts/totals.json",
    caption="Table 2: per-country mortality totals (2020–2021)",
    tags=["result", "table"],
)
print(summary)
