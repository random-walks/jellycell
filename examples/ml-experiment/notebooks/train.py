# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "matplotlib"]
# ///

# %% [markdown]
# # Tiny training loop
#
# A one-parameter linear regression fit with gradient descent, plus a
# loss curve and final metrics. Every run dumps:
#
# - `artifacts/checkpoint.json` — the final weight + full loss history.
# - `artifacts/metrics.json` — end-of-training summary (for the tearsheet table).
# - `artifacts/loss_curve.png` — training loss vs. epoch.

# %% tags=["jc.setup", "name=config"]
EPOCHS = 40
LR = 0.02
SEED = 0
TRUE_W = 1.7
NOISE = 0.25

# %% tags=["jc.load", "name=toy_dataset"]
# Noisy linear data: y ≈ TRUE_W * x + ε.
import numpy as np

rng = np.random.default_rng(SEED)
x = rng.uniform(-1.0, 1.0, size=128)
noise = rng.normal(0.0, NOISE, size=x.shape)
y = TRUE_W * x + noise
print(f"dataset: {len(x)} points   target w: {TRUE_W}")

# %% tags=["jc.step", "name=train", "deps=toy_dataset", "deps=config"]
# Vanilla full-batch gradient descent on MSE.
w = 0.0
loss_history: list[float] = []
for _ in range(EPOCHS):
    pred = w * x
    grad = float(np.mean(2.0 * (pred - y) * x))
    w -= LR * grad
    loss_history.append(float(np.mean((pred - y) ** 2)))
print(f"fitted w: {w:.4f}   target w: {TRUE_W}")
print(f"final loss: {loss_history[-1]:.4f}")

# %% tags=["jc.figure", "name=loss_curve", "deps=train"]
import matplotlib.pyplot as plt

import jellycell.api as jc

fig, ax = plt.subplots(figsize=(7, 3.2))
ax.plot(range(1, EPOCHS + 1), loss_history, color="#4f46e5", linewidth=1.6)
ax.set_xlabel("Epoch")
ax.set_ylabel("MSE loss")
ax.set_title("Training loss per epoch")
ax.grid(alpha=0.3)
fig.tight_layout()
jc.figure(path="artifacts/loss_curve.png", fig=fig)

# %% tags=["jc.step", "name=metrics", "deps=train"]
metrics = {
    "epochs": EPOCHS,
    "learning_rate": LR,
    "final_weight": round(w, 4),
    "target_weight": TRUE_W,
    "final_loss": round(loss_history[-1], 4),
    "initial_loss": round(loss_history[0], 4),
    "weight_error_abs": round(abs(w - TRUE_W), 4),
}
jc.save(metrics, "artifacts/metrics.json")
print(metrics)

# %% tags=["jc.step", "name=checkpoint", "deps=train"]
# Full loss history lives in the checkpoint alongside the weight. Real
# projects would write tensors here; jellycell's cache is content-
# addressed so identical checkpoints dedup on disk.
jc.save({"weight": w, "history": loss_history}, "artifacts/checkpoint.json")
