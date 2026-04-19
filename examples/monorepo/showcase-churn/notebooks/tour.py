# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

# %% [markdown]
# # Churn showcase
#
# A sibling jellycell project in the same monorepo. Its cache and
# site directory are local to this subdirectory — re-running the
# marketing showcase next door doesn't invalidate anything here.

# %% tags=["jc.load", "name=cohort"]
cohort = [
    {"user": 1, "months": 12, "churned": False},
    {"user": 2, "months": 3, "churned": True},
    {"user": 3, "months": 8, "churned": False},
    {"user": 4, "months": 1, "churned": True},
]

# %% tags=["jc.step", "name=retention", "deps=cohort"]
import jellycell.api as jc

active = [c for c in cohort if not c["churned"]]
retention = len(active) / len(cohort)
report = {"n": len(cohort), "retained": len(active), "retention": round(retention, 3)}
jc.save(report, "artifacts/retention.json", caption="Cohort retention")
print(f"retention = {retention:.1%}")
