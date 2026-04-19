# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

# %% [markdown]
# # Marketing showcase
#
# One jellycell project in a multi-project monorepo. Its
# `.jellycell/cache/`, `site/`, and `artifacts/` live alongside the
# notebook — totally isolated from sibling showcases.

# %% tags=["jc.load", "name=raw"]
raw = {"impressions": 12_400, "clicks": 312, "conversions": 28}

# %% tags=["jc.step", "name=summary", "deps=raw"]
import jellycell.api as jc

ctr = raw["clicks"] / raw["impressions"]
cvr = raw["conversions"] / raw["clicks"]
summary = {**raw, "ctr": round(ctr, 4), "cvr": round(cvr, 4)}
jc.save(summary, "artifacts/summary.json", caption="Funnel summary")
print(f"CTR {ctr:.2%}, CVR {cvr:.2%}")
