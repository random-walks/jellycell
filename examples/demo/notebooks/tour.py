# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

# %% [markdown]
# # jellycell tour
#
# A minimal demonstration of the cell types, tags, and the `jc.*` API.
# Use `jellycell run` to execute, then `jellycell view` to browse.

# %% [markdown]
# ## 1. A `jc.load` cell
#
# Conventionally, `jc.load` cells read from `data/`. Here we fake it by
# constructing a literal so the demo stays dependency-free.

# %% tags=["jc.load", "name=raw"]
raw = {"a": 1, "b": 2, "c": 3}
print(f"loaded {len(raw)} entries")

# %% [markdown]
# ## 2. A transform step with explicit dep

# %% tags=["jc.step", "name=totals", "deps=raw"]
totals = sum(raw.values())
print(f"totals = {totals}")

# %% [markdown]
# ## 3. Saving an artifact via `jc.save`

# %% tags=["jc.step", "name=persist", "deps=totals"]
import jellycell.api as jc

summary = {"raw": raw, "totals": totals}
path = jc.save(summary, "artifacts/summary.json")
print(f"wrote {path}")

# %% [markdown]
# ## 4. An `jc.note` markdown cell (rendered, not executable)
#
# This style of cell is useful for narrative-only commentary between
# computations.

# %% tags=["jc.step", "name=derived", "deps=totals"]
squared = totals**2
print(f"squared = {squared}")
