# jellycell

> A living catalogue for reproducible analyses: plain-text notebooks, content-hashed output caching, live HTML viewer.

**Status:** `v0.1.0` — first real release. All v0 spec phases shipped (run + cache + render + view + export + agent surface). See [CHANGELOG.md](CHANGELOG.md).

## What it does

- **Plain-text notebooks** — `.py` files in jupytext percent format, with PEP-723 dependency declarations at the top. Diffable, greppable, `uv run`-able.
- **Content-addressed cache** — every cell's output is keyed on `(source, deps, env)`. Re-run is a cache hit; change a cell, only the affected subgraph re-executes.
- **Live HTML catalogue** — `jellycell view` serves a project-wide report with side-nav, artifact browser, and SSE-backed live reload while you edit.
- **Agent-friendly** — every command supports `--json`; `jellycell prompt` emits a canonical guide so Claude Code / OpenAI agents drop into a project without onboarding.

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
# write notebooks/analysis.py (see docs/file-format.md)
jellycell run notebooks/analysis.py
jellycell view            # requires [server] extra
```

Full docs: **https://jellycell.readthedocs.io**

## Status by phase

| Phase | Goal                                    | Ships as  | Status  |
| ----- | --------------------------------------- | --------- | ------- |
| 0     | Skeleton; PyPI; CI                      | `v0.0.1`  | ✅ done |
| 1     | `jellycell init` + `lint`               | (interim) | ✅ done |
| 2     | `jellycell run` + cache + `jc.*` API    | `v0.0.2`  | ✅ done |
| 3     | `jellycell render` (HTML output)        | (interim) | ✅ done |
| 4     | `jellycell view` (live viewer)          | (interim) | ✅ done |
| 5     | `jellycell export` (ipynb/md)           | (interim) | ✅ done |
| 6     | Agent guide + polish                    | `v0.1.0`  | ✅ done |

## License

Apache-2.0. See [LICENSE](LICENSE).
