# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

# %% [markdown]
# # jellycell tour
#
# Exercises the core `jc.*` API without external deps. Run with
# `jellycell run notebooks/tour.py`, then `jellycell export tearsheet
# notebooks/tour.py` to drop a curated summary into `manuscripts/`.

# %% [markdown]
# ## 1. Config — a `kind=setup` cell
#
# Setup cells surface their source in the tearsheet so parameters are
# obvious at a glance.

# %% tags=["jc.setup", "name=config"]
USERS = 120
SESSIONS = 450
CONVERSIONS = 38

# %% [markdown]
# ## 2. Load — simulate reading project inputs
#
# Real projects would read from `data/`; we keep this demo dep-free by
# constructing a literal.

# %% tags=["jc.load", "name=raw"]
raw = {"users": USERS, "sessions": SESSIONS, "conversions": CONVERSIONS}
print(f"loaded {len(raw)} metrics")

# %% [markdown]
# ## 3. Transform with an explicit dep

# %% tags=["jc.step", "name=rate", "deps=raw"]
conversion_rate = raw["conversions"] / raw["sessions"]
print(f"conversion rate: {conversion_rate:.2%}")

# %% [markdown]
# ## 4. Persist a JSON summary via `jc.save`
#
# The tearsheet auto-renders the saved JSON as a key/value table.

# %% tags=["jc.step", "name=summary", "deps=rate"]
import jellycell.api as jc

summary = {
    "total_users": raw["users"],
    "total_sessions": raw["sessions"],
    "conversion_rate": round(conversion_rate, 4),
    "conversions": raw["conversions"],
}
jc.save(summary, "artifacts/summary.json")

# %% [markdown]
# ## 5. Round-trip via `jc.load`
#
# `jc.load` registers an implicit dep edge on the producing cell
# (`name=summary`). Edit the summary cell → this cell's cache invalidates
# automatically, no hand-written `deps=` needed.

# %% tags=["jc.step", "name=roundtrip"]
reloaded = jc.load("artifacts/summary.json")
assert reloaded == summary
print(f"reloaded {len(reloaded)} keys: {sorted(reloaded)}")

# %% [markdown]
# ## 6. Derived metric — exercises cache invalidation
#
# Change `CONVERSIONS` in the setup cell and only the downstream
# subgraph (`rate` → `summary` → this cell) re-runs.

# %% tags=["jc.step", "name=derived", "deps=summary"]
headline = f"{raw['conversions']} of {raw['sessions']} sessions converted"
jc.save({"headline": headline}, "artifacts/headline.json")
print(headline)
