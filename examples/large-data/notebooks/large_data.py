# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pandas", "pyarrow", "matplotlib"]
# ///

# %% [markdown]
# # Large-data workflow
#
# Demonstrates the **git-ignore the bulky bits, commit the story** pattern:
#
# - `data/seed.json` — a tiny committed seed controls generation. Edit the
#   seed and the downstream cache invalidates.
# - `artifacts/large_data/sample_*.parquet` — generated dump, **git-ignored**
#   (see [`.gitignore`](../.gitignore)). Reviewers re-run `jellycell run` to
#   reproduce it locally; the bytes never hit version control.
# - `artifacts/large_data/headline.json` — a small committed digest. Fits
#   in the tearsheet as a key/value table so reviewers see the last-run
#   stats on GitHub without needing the parquet.
#
# The project has `max_committed_size_mb = 10` set low so the generated
# parquet trips the warning at the end of `jellycell run`.

# %% tags=["jc.setup", "name=config"]
# 500k rows × 12 features ≈ 48 MB parquet. Enough to trip the 10 MB
# max_committed_size_mb warning below — dial it up to 5_000_000 for a
# "really big" run, down to 50_000 for a fast smoke test. The downstream
# cache-key tracks this value, so the subgraph re-runs on any change.
N_ROWS = 500_000
N_FEATURES = 12
SEED = 42

# %% tags=["jc.step", "name=sample", "deps=config"]
# Generate the "big" parquet. Not hand-written data — a reproducible
# synthetic sample derived from the seed so any reviewer gets identical
# bytes without checking in the file.
#
# Reads `data/seed.json` directly via `jc.load` inside this cell (rather
# than through a separate `seed` cell) so the subgraph works cleanly
# across mixed cache-hit / re-run boundaries — the seed config doesn't
# need to live in the kernel's memory.
import numpy as np
import pandas as pd

import jellycell.api as jc

seed_cfg = jc.load("data/seed.json")
rng = np.random.default_rng(SEED + seed_cfg["offset"])
X = rng.normal(loc=seed_cfg["mean"], scale=seed_cfg["scale"], size=(N_ROWS, N_FEATURES))
df = pd.DataFrame(X, columns=[f"f{i}" for i in range(N_FEATURES)])
df["label"] = (df["f0"] + 0.5 * df["f1"] - 0.25 * df["f2"] > 0).astype(int)

# Explicit path keeps the .gitignore glob simple.
out = jc.save(df, "artifacts/large_data/sample_dataset.parquet")
print(f"{len(df):,} rows × {df.shape[1]} cols → {out}")

# %% tags=["jc.step", "name=headline", "deps=sample"]
# A compact digest of the underlying data. This IS committed (few KB) and
# carries enough summary stats for the tearsheet. It's a good pattern:
# commit the summary, git-ignore the bulk.
df = jc.load("artifacts/large_data/sample_dataset.parquet")
headline = {
    "rows": int(len(df)),
    "features": int(df.shape[1] - 1),
    "positive_rate": round(float(df["label"].mean()), 4),
    "feature_mean": round(float(df.drop(columns=["label"]).values.mean()), 4),
    "feature_std": round(float(df.drop(columns=["label"]).values.std()), 4),
    "size_mb": round(out.stat().st_size / (1024 * 1024), 2),
}
jc.save(headline, "artifacts/large_data/headline.json")
print(headline)

# %% tags=["jc.figure", "name=class_balance", "deps=headline"]
# A tiny figure that fits in a tearsheet. Path-less — layout=by_notebook
# from jellycell.toml drops it under artifacts/large_data/ automatically.
import matplotlib.pyplot as plt

counts = df["label"].value_counts().sort_index()
fig, ax = plt.subplots(figsize=(5, 3))
ax.bar(["0", "1"], counts.values, color=["#6b7280", "#4f46e5"])
ax.set_ylabel("Count")
ax.set_title(f"Label balance (n={len(df):,})")
ax.grid(alpha=0.3, axis="y")
for i, v in enumerate(counts.values):
    ax.text(i, v, f"{v:,}", ha="center", va="bottom", fontsize=9)
fig.tight_layout()
jc.figure(fig=fig)
