---
hide-toc: false
---

# jellycell

***A living catalogue for reproducible analyses. Plain-text notebooks, content-hashed output caching, live HTML viewer. Agent-friendly from day one.***

## What it does

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

## Start here

::::{grid} 1 2 2 2
:gutter: 3
:margin: 4 4 0 0

:::{grid-item-card} {octicon}`rocket;1.5em` &nbsp; Getting started
:link: getting-started
:link-type: doc

Install, scaffold a project, run your first notebook end-to-end in
under five minutes.

+++
**Start the walkthrough »**
:::

:::{grid-item-card} {octicon}`book;1.5em` &nbsp; User guide
:link: project-layout
:link-type: doc

Project layout, notebook file format, `jc.*` API, tearsheets,
artifacts, the CLI — everything you touch day-to-day.

+++
**Open the guide »**
:::

:::{grid-item-card} {octicon}`code-square;1.5em` &nbsp; Reference
:link: reference/index
:link-type: doc

The living architecture + §10 contracts + internals. Authoritative
source for how jellycell is built and what it promises.

+++
**Read the reference »**
:::

:::{grid-item-card} {octicon}`tools;1.5em` &nbsp; Contributing
:link: development/contributing
:link-type: doc

Dev setup, versioning policy, how to add commands + lint rules, how
releases are cut. Read before opening a PR.

+++
**Open the dev guide »**
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
:maxdepth: 2
:caption: Reference

reference/index
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
:caption: History

spec/v0
```
