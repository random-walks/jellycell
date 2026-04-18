# ml-experiment

A self-contained training run: one-parameter linear regression fit with
gradient descent, plus a loss curve and a metrics JSON. The
[`model-card.md`](manuscripts/model-card.md) hand-authored writeup
captures the usual ML-experiment-log bits (hypothesis, methodology,
results, limitations) alongside the auto-generated
[tearsheet](manuscripts/tearsheets/train.md) that carries the figures
and numbers.

## Bootstrap

```bash
# uv (preferred — installs numpy/matplotlib via [examples])
uv sync
cd examples/ml-experiment
uv run jellycell run notebooks/train.py -m "baseline, LR=0.02 EPOCHS=40"
uv run jellycell export tearsheet notebooks/train.py
uv run jellycell view                                # needs [server]

# pip
pip install 'jellycell[server,examples]'
jellycell run notebooks/train.py -m "baseline, LR=0.02 EPOCHS=40"
jellycell export tearsheet notebooks/train.py
jellycell view
```

## What this example shows

- **`kind=setup`** — the `config` cell holds hyperparameters (`EPOCHS`,
  `LR`, `SEED`, `TRUE_W`, `NOISE`). The tearsheet surfaces the whole
  source as a fenced block, so reviewers see the hyperparams at a glance.
- **Artifact-per-purpose** — `checkpoint.json` keeps the full loss
  history, `metrics.json` holds the end-of-run digest. The tearsheet
  flattens `metrics.json` into a two-column table.
- **Figure inlined in the tearsheet** — `loss_curve.png` drops into
  the tearsheet via a relative path.
- **Deterministic, CI-friendly** — `SEED = 0` + small dataset means CI
  gets the same loss curve every time. Swap `TRUE_W` or `NOISE` to vary
  the experiment.

## Layout

```
ml-experiment/
├── jellycell.toml
├── notebooks/train.py
├── artifacts/
│   ├── checkpoint.json                     # full loss history + weight
│   ├── metrics.json                        # end-of-run digest
│   └── loss_curve.png                      # training curve
├── reports/train.html                      # HTML report
└── manuscripts/
    ├── README.md
    ├── model-card.md                       # hand-authored experiment log
    └── tearsheets/
        └── train.md                        # auto-generated dashboard
```

## Extending

Real projects will swap in pytorch / sklearn / jax. The `jc.*` contract
is unchanged: `jc.save(weights, "artifacts/checkpoint.pkl")` for a
pickled weights blob, `jc.figure(fig=fig)` for any matplotlib chart,
`jc.save(metrics_dict, "artifacts/metrics.json")` for the summary. The
tearsheet auto-picks up figures and JSONs; hand-edit
`manuscripts/model-card.md` to evolve the narrative alongside.
