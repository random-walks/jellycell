# large-data

Demonstrates jellycell's **large-data workflow** — the "commit the story,
git-ignore the bulk" pattern. The notebook generates a ~50 MB parquet
(deliberately crosses the 10 MB soft threshold set in this project's
`jellycell.toml`) so you can see:

- The `jellycell run` post-run warning flagging the oversized artifact.
- A `.gitignore` glob keeping the parquet out of version control.
- A tiny committed `headline.json` digest that fits in the tearsheet.
- `[artifacts] layout = "by_notebook"` filing everything under
  `artifacts/large_data/` so agents immediately know the producer.

Runs cheaply (~1 s); scale `N_ROWS` in the `config` cell to experiment
with the warning threshold.

## Bootstrap

```bash
# uv (preferred — installs numpy/pandas/pyarrow/matplotlib via [examples])
uv sync
cd examples/large-data
uv run jellycell run notebooks/large_data.py
uv run jellycell export tearsheet notebooks/large_data.py
uv run jellycell view                                # needs [server]

# pip
pip install 'jellycell[server,examples]'
jellycell run notebooks/large_data.py
jellycell export tearsheet notebooks/large_data.py
jellycell view
```

## What gets committed vs. regenerated

```
examples/large-data/
├── jellycell.toml                        # [artifacts] config lives here
├── .gitignore                            # globs the parquet dumps away
├── data/seed.json                        # tiny committed input (controls generation)
├── notebooks/large_data.py               # the pipeline (committed)
├── artifacts/large_data/
│   ├── class_balance.png                 # committed (small)
│   ├── headline.json                     # committed (tiny digest)
│   └── sample_dataset.parquet            # NOT committed — regenerate locally
├── reports/                              # HTML reports (committed; small)
└── manuscripts/
    ├── README.md
    ├── data-notes.md                     # hand-authored reproducibility protocol
    └── tearsheets/
        └── large_data.md                 # auto-generated dashboard
```

The pattern: anything small enough to fit in the tearsheet is committed;
anything big is git-ignored and reproducible from the seed + notebook.

## What this example shows

- **`[artifacts] max_committed_size_mb = 10`** — the post-run warning
  fires because `sample_dataset.parquet` is ~48 MB. Output:

  ```
  note: 1 artifact(s) exceed 10 MB — consider `.gitignore` or Git LFS:
    large_data:2 (sample) artifacts/large_data/sample_dataset.parquet 48.97 MB
  ```

  Tune the threshold (or set to `0` to disable) in `jellycell.toml`.

- **`[artifacts] layout = "by_notebook"`** — `jc.figure(fig=fig)` with
  no explicit path writes to `artifacts/large_data/class_balance.png`
  automatically. Agents reading the artifact tree know what notebook
  produced what without touching manifests.

- **Seed-controlled reproducibility** — `data/seed.json` drives the
  random generator. Edit it and the downstream cache invalidates via
  the dep edge `jc.load` registers on the seed file.

- **`headline.json` as a committed digest** — 135 bytes of summary
  stats that fit inline in the tearsheet, so reviewers see the
  last-run summary on GitHub without needing the parquet.

## When to use LFS instead

If git-ignoring the artifact means reviewers can't easily inspect a
historical run, switch to [Git LFS](https://git-lfs.com/):

```bash
git lfs install
git lfs track "artifacts/large_data/*.parquet"
git add .gitattributes
```

…and remove the matching glob from `.gitignore`. LFS keeps the bytes
addressable via commit SHA but stores them outside the main pack file.
Still worth running `jellycell run` to regenerate during active
development — LFS is for historical checkpoints, not every commit.

## Manuscripts

- [`manuscripts/data-notes.md`](manuscripts/data-notes.md) —
  hand-authored reproducibility protocol + notes on the generation.
- [`manuscripts/tearsheets/large_data.md`](manuscripts/tearsheets/large_data.md)
  — auto-generated dashboard with the headline digest and class-balance
  figure.
