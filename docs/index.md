---
hide-toc: false
---

# jellycell

**A living catalogue for reproducible analyses.** Plain-text notebooks, content-hashed output caching, live HTML viewer. Agent-friendly from day one.

:::{note}
**Status: pre-alpha.** The scaffolding is here; features land in phases. The [v0 spec](spec/v0.md) documents the full target architecture. Current release: `v0.0.1` (skeleton).
:::

## What it does (when finished)

::::{grid} 1 2 2 2
:gutter: 2

:::{grid-item-card} Plain-text notebooks
`.py` files in jupytext percent format with PEP-723 dependency declarations. Diffable, greppable, `uv run`-able.
:::

:::{grid-item-card} Content-addressed cache
Every cell's output is keyed on `(source, deps, env)`. Re-run is a cache hit; change a cell, only the affected subgraph re-executes.
:::

:::{grid-item-card} Live HTML catalogue
`jellycell view` serves a project-wide report with side-nav, artifact browser, and SSE-backed live reload while you edit.
:::

:::{grid-item-card} Agent-friendly
Every command supports `--json`; `jellycell prompt` emits a canonical guide so Claude Code / OpenAI agents drop in without onboarding.
:::
::::

## Install

```bash
pip install jellycell            # CLI only
pip install 'jellycell[server]'  # with `jellycell view`
```

Requires Python ≥ 3.11.

## Contents

```{toctree}
:maxdepth: 2
:caption: Using jellycell

getting-started
file-format
project-layout
cli-reference
agent-guide
```

```{toctree}
:maxdepth: 1
:caption: API

api/index
```

```{toctree}
:maxdepth: 1
:caption: Contributing

development/dev-setup
development/contributing
development/preview
development/adding-commands
development/adding-lint-rules
development/releasing
```

```{toctree}
:maxdepth: 1
:caption: Reference

spec/v0
```
