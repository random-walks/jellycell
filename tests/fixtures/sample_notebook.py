# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2"]
# ///

# %% [markdown]
# # Sample notebook
#
# Used by format, lint, and integration tests as a canonical example.

# %% tags=["jc.load", "name=raw"]
import pandas as pd

raw = pd.DataFrame({"country": ["A", "B"], "deaths": [10, 20]})

# %% tags=["jc.step", "name=summary", "deps=raw"]
summary = raw.groupby("country")["deaths"].sum()

# %% tags=["jc.figure", "deps=summary"]
print(summary)
