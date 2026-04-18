# /// script
# requires-python = ">=3.11"
# dependencies = []
#
# [tool.jellycell]
# timeout_seconds = 180
# ///

# %% [markdown]
# # Mortality trend analysis
#
# A paper-shaped jellycell project. Narrative text lives alongside
# reproducible compute; the final report is rendered via
# `jellycell render` and shipped with the manuscript.

# %% tags=["jc.load", "name=raw"]
import csv
from pathlib import Path

with Path("data/sample.csv").open() as f:
    rows = list(csv.DictReader(f))
print(f"loaded {len(rows)} rows")

# %% tags=["jc.step", "name=per_country_totals", "deps=raw"]
totals: dict[str, int] = {}
for row in rows:
    totals.setdefault(row["country"], 0)
    totals[row["country"]] += int(row["deaths"])
for country, total in sorted(totals.items(), key=lambda kv: -kv[1]):
    print(f"{country}: {total:,}")

# %% tags=["jc.step", "name=save_summary", "deps=per_country_totals"]
import jellycell.api as jc

jc.save(totals, "artifacts/totals.json")

# %% [markdown]
# ## Next steps
#
# - Extend `data/sample.csv` with the real WHO dataset.
# - Add per-year figures via a `jc.figure` cell.
# - Hand-off to `manuscripts/paper.md` (see adjacent directory) for
#   the narrative write-up.
