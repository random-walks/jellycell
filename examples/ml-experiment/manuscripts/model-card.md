# Model card — one-parameter linear regression

Hand-authored experiment log. Pairs with the auto-generated
[tearsheet](tearsheets/train.md) for the loss curve and metrics table.

## Problem

Fit `y = w · x` from noisy samples `(xᵢ, yᵢ)` where `yᵢ = 1.7 · xᵢ + εᵢ`,
`εᵢ ∼ Normal(0, 0.25)`. Deliberately small so the notebook runs in ~1s
and CI stays cheap, but the structure is the real one — full-batch
gradient descent on MSE loss.

## Hypothesis

With `LR = 0.02` and `EPOCHS = 40`, the gradient descent should converge
toward `w ≈ 1.7`. Final loss should be close to the irreducible noise
floor (σ² = 0.0625).

## Methodology

See [`notebooks/train.py`](../notebooks/train.py):

1. **`config`** cell declares hyperparams. Tagged `kind=setup` so the
   tearsheet surfaces them explicitly.
2. **`toy_dataset`** draws 128 points from the true distribution.
3. **`train`** runs full-batch GD on MSE for `EPOCHS` iterations and
   keeps the loss history.
4. **`loss_curve`** plots loss-vs-epoch.
5. **`metrics`** persists the end-of-training digest to
   `artifacts/metrics.json`.
6. **`checkpoint`** persists the weight + full loss history to
   `artifacts/checkpoint.json`.

Everything is seeded (`SEED = 0`), so CI gets identical numbers on
every run.

## Results

See the tearsheet table for the live values. At the time of writing:

- **Fitted `w ≈ 0.79`**, vs. target `1.7`. Close-but-not-there — with
  only 40 epochs and `LR = 0.02` the optimizer hasn't converged. Bumping
  `EPOCHS` to 200 gets `w` within ~0.05 of target.
- **Final loss ≈ 0.41** vs. **initial loss ≈ 1.20** — monotone
  decrease, no oscillation, no divergence. Loss curve confirms.

## Limitations

- 128 points is a toy. Sampling variance matters.
- Full-batch GD isn't what production-scale ML uses; this is a
  pedagogical demo.
- No held-out eval set. For real models you'd split `(x, y)` and report
  out-of-sample MSE alongside training loss.

## What I'd change next

1. Tune `EPOCHS` / `LR` for actual convergence (see note above).
2. Add a held-out 20% split, save val loss per epoch, plot both curves
   in one figure via `jc.figure`.
3. Replace the hand-rolled GD with `sklearn.linear_model.LinearRegression`
   to sanity-check the closed-form solution.

## Links

- Notebook: [`../notebooks/train.py`](../notebooks/train.py)
- Tearsheet: [`tearsheets/train.md`](tearsheets/train.md)
- Artifacts: [`../artifacts/`](../artifacts/)
