# jellycell

[![PyPI](https://img.shields.io/pypi/v/jellycell?color=blue)](https://pypi.org/project/jellycell/)
[![Docs](https://img.shields.io/badge/docs-readthedocs-blue)](https://jellycell.readthedocs.io)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/jellycell)](https://pypi.org/project/jellycell/)

***A living catalogue for reproducible analyses. Plain-text notebooks, content-addressed cell-output caching, live HTML viewer. Agent-friendly from day one.***

## Why jellycell

Jupyter notebooks are great for exploration and awful for everything after. They diff poorly, store outputs alongside code, make provenance opaque, and have no story for "which step produced this file?" — so analyses drift, results become unreproducible, and the notebook gets rewritten as a script anyway.

jellycell keeps the things that made notebooks useful (cell-level thinking, rich outputs, narrative + code interleaved) and fixes what made them painful:

- **Source is plain Python.** Notebooks are `.py` files in jupytext percent format with a PEP-723 dependency header. Diffable, greppable, `uv run`-able. No JSON-wrapped base64.
- **Outputs are content-addressed.** Every cell's output is keyed on `(normalized source, declared + detected deps, lockfile-aware env hash)`. Re-run → cache hit. Change a cell → only that cell + its dependents re-execute. Outputs live in a sidecar cache, not in your commits.
- **Provenance is first-class.** Every artifact is tagged with the cell + notebook + cache key that produced it. `jc.load("artifacts/foo.json")` implicitly declares the dep edge. No hand-written DAGs.
- **HTML reports are free.** `jellycell render` produces byte-identical static HTML; `jellycell view` serves the same pages live with SSE-backed reload while you edit. Side-nav, artifact browser, no build step.
- **Agents drop in without onboarding.** Every CLI command supports `--json` with a versioned schema. `jellycell prompt` emits a canonical agent guide — the exact instructions Claude Code or your own agent needs to work in the project without hand-holding.

## Install

```bash
pip install jellycell            # CLI only (no live viewer)
pip install 'jellycell[server]'  # with `jellycell view`
```

Requires Python ≥ 3.11.

## Quickstart

```bash
jellycell init my-project
cd my-project

# Scaffold a notebook
jellycell new tour
# edit notebooks/tour.py in your editor of choice

# Run it — first time executes, subsequent runs hit the cache
jellycell run notebooks/tour.py

# Build static HTML reports
jellycell render notebooks/tour.py

# Or serve the live viewer with reload on save (requires [server] extra)
jellycell view
```

Inside a cell, the `jc.*` helpers work transparently:

```python
# %% cell-id=tour:1 name=raw
import pandas as pd
df = pd.read_csv("data/sales.csv")
jc.save(df, "artifacts/sales.parquet")

# %% cell-id=tour:2 name=summary deps=raw
df = jc.load("artifacts/sales.parquet")
summary = df.describe()
jc.table(summary)
```

Change `tour:1` → `tour:2` invalidates on the next run. Edit nothing → both hit the cache.

Full docs: **https://jellycell.readthedocs.io**

## Composition, not reinvention

jellycell's value is the **composition**, not the parts. We piggyback on the best tools in the Jupyter ecosystem:

| We piggyback on | For |
| --- | --- |
| **jupytext** | `.py` ↔ notebook IR |
| **jupyter-client** | kernel subprocess + messaging |
| **nbformat** | `.ipynb` round-trip |
| **diskcache** | content-addressed blob store |
| **nbconvert** (output helpers) | mime bundle → safe HTML |
| **markdown-it-py + MyST plugins** | markdown rendering |
| **watchfiles + sse-starlette** | live reload |
| **pydantic + typer** | CLI + config + schemas |

The bits we own are the ones that tie these together: tag vocabulary, cache key derivation, manifest format, per-cell orchestration, page shell, dep graph, agent guide. The full piggyback map is in [`docs/reference/architecture.md`](docs/reference/architecture.md).

## Is this for you?

**Probably yes if:**

- You write analyses in notebooks and wish they diffed.
- You keep rerunning a 10-minute cell to regenerate one plot.
- You need reviewers or agents to understand what produced what.
- You want a single project-wide HTML report, not a directory of disconnected `.ipynb` files.

**Probably no if:**

- You want a fully-featured cloud notebook platform.
- You need real-time collaboration / multiplayer editing.
- Your workflow is tightly coupled to JupyterLab extensions.

## Project structure

```
my-project/
├── jellycell.toml          # project config
├── notebooks/              # .py notebooks (jupytext percent format)
├── data/                   # inputs
├── artifacts/              # jc.save outputs
├── reports/                # rendered HTML (jellycell render)
└── .jellycell/cache/       # content-addressed cache (gitignored)
```

## Documentation

- **Tutorial**: [getting-started](https://jellycell.readthedocs.io/en/stable/getting-started.html)
- **Notebook format**: [file-format](https://jellycell.readthedocs.io/en/stable/file-format.html)
- **Project layout**: [project-layout](https://jellycell.readthedocs.io/en/stable/project-layout.html)
- **CLI reference**: [cli-reference](https://jellycell.readthedocs.io/en/stable/cli-reference.html)
- **Agent guide**: [agent-guide](https://jellycell.readthedocs.io/en/stable/agent-guide.html) — what `jellycell prompt` emits
- **Reference**: [docs/reference/](docs/reference/index.md) — living architecture + §10 contracts
- **Historical spec**: [docs/spec/v0.md](docs/spec/v0.md) — frozen genesis / v1.0 build spec

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/development/](docs/development/). Short version: bugfix PRs are welcome and bump patch; feature PRs should open an issue first. The three §10 contracts (`--json` schemas, cache key algorithm, agent guide content) are deliberate ceremonies — read [docs/development/releasing.md](docs/development/releasing.md) before touching them.

## License

Apache-2.0. See [LICENSE](LICENSE).
