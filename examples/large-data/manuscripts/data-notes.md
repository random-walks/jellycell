# Data-generation notes

Hand-authored reproducibility protocol. Pairs with the auto-generated
[tearsheet](tearsheets/large_data.md) for the latest-run numbers.

## What gets generated, from what

- **Input:** [`data/seed.json`](../data/seed.json) — 4 scalar fields
  (`offset`, `mean`, `scale`, `notes`). Committed; anyone cloning the
  repo starts from identical bytes.
- **Script:** [`notebooks/large_data.py`](../notebooks/large_data.py) —
  the `sample` cell draws `N_ROWS × N_FEATURES` from
  `Normal(seed_cfg.mean, seed_cfg.scale)`, seeded with
  `SEED + seed_cfg.offset` so the generator is deterministic.
- **Output:** `artifacts/large_data/sample_dataset.parquet` (~48 MB at
  `N_ROWS = 500_000`). **Not committed** — see `.gitignore`. Re-run
  `jellycell run notebooks/large_data.py` to regenerate.

## Why we commit the digest instead of the data

`headline.json` is 135 bytes. It carries:

- Row count (sanity-check that `N_ROWS` hasn't drifted).
- Feature count (sanity-check column schema).
- Positive-label rate (sanity-check the `label` derivation).
- Per-feature mean + std (sanity-check the distribution didn't shift).
- File size in MB (sanity-check the compression).

That's enough for a reviewer to say "yes, my regenerated parquet
matches your run" without downloading 50 MB. Any drift in the numbers
above signals either a seed change, a generator bug, or a
library-version mismatch — all of which warrant a conversation.

## Reproducibility protocol

To reproduce a historical run exactly:

1. `git checkout <commit>` at the known-good point.
2. `uv sync` (the lockfile bytes are part of the cache-key `env_hash`,
   so an upstream library bump invalidates the cache cleanly).
3. `jellycell run notebooks/large_data.py`.
4. Compare `headline.json` — should match the committed version byte
   for byte.

If you need the parquet itself for an audit (and git-ignore isn't
appropriate), see the "When to use LFS instead" section in the
[top-level README](../README.md#when-to-use-lfs-instead).

## Scaling up

The commit here sets `N_ROWS = 500_000` so the example stays CI-cheap.
Three knobs to play with:

- **`N_ROWS`** — linear scaling of file size. 5M rows ≈ 480 MB parquet.
- **`N_FEATURES`** — also linear.
- **Seed** — change `SEED` or `seed_cfg.offset` to get a different
  deterministic draw. The cache invalidates; downstream `headline.json`
  updates; re-run the tearsheet.

## Links

- Notebook: [`../notebooks/large_data.py`](../notebooks/large_data.py)
- Tearsheet: [`tearsheets/large_data.md`](tearsheets/large_data.md)
- Artifacts tree: [`../artifacts/large_data/`](../artifacts/large_data/)
  (parquet git-ignored; digest + figure committed)
