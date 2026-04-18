# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

# %% [markdown]
# # Tiny training loop
#
# Skeleton of an ML experiment. Real runs would depend on NumPy / PyTorch;
# this demo stays dependency-free so it runs on CI.

# %% tags=["jc.setup", "name=config"]
EPOCHS = 5
LR = 0.1
SEED = 0

# %% tags=["jc.load", "name=toy_dataset"]
# Stand-in for a data-loader. Returns (x, y) pairs.
import random

random.seed(SEED)
dataset = [(random.random(), random.random() * 2 + 1.0) for _ in range(64)]
print(f"dataset: {len(dataset)} pairs")

# %% tags=["jc.step", "name=train", "deps=toy_dataset", "deps=config"]
# A minimal "training loop" just for illustration.
loss_history = []
w = 0.0
for epoch in range(EPOCHS):
    total = 0.0
    for x, y in dataset:
        pred = w * x
        grad = 2 * (pred - y) * x
        w -= LR * grad
        total += (pred - y) ** 2
    loss = total / len(dataset)
    loss_history.append(loss)
    print(f"epoch {epoch}: loss={loss:.4f} w={w:.4f}")

# %% tags=["jc.step", "name=persist_checkpoint", "deps=train"]
import jellycell.api as jc

jc.save({"weight": w, "history": loss_history}, "artifacts/checkpoint.json")

# %% [markdown]
# Real projects would write binary artefacts (model weights, tensors)
# with an appropriate format — jellycell's cache is content-addressed,
# so checkpoint blobs dedup naturally.
