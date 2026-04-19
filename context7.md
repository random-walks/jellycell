# jellycell

**A living catalogue for reproducible analyses.** Plain-text `.py` notebooks in jupytext percent format, content-addressed per-cell output cache, live HTML viewer. Agent-friendly by design.

- Docs: https://jellycell.readthedocs.io/
- Repo: https://github.com/random-walks/jellycell
- PyPI: https://pypi.org/project/jellycell/
- Agent guide (canonical, §10.3): https://jellycell.readthedocs.io/en/latest/agent-guide.html
- Full docs concat for agents: https://jellycell.readthedocs.io/en/latest/llms-full.txt

## What it does

A notebook is a plain `.py` file with a PEP-723 dependency header and jupytext percent-format cell markers. Run it with `jellycell run` — every cell's output is cached under `(normalized source, declared + detected deps, lockfile-aware env hash)`, so re-runs hit the cache instantly and editing a cell only re-executes that cell plus its dependents. Render it with `jellycell render` for a self-contained HTML catalogue, or serve it live with `jellycell view` (SSE reload on save).

Consumers (humans and agents) get two surfaces: a CLI where every command supports `--json` with a versioned schema, and a `jc.*` runtime API for inline use inside cells.

## Install

```bash
pip install jellycell            # CLI only
pip install 'jellycell[server]'  # adds the live viewer
```

Requires Python ≥ 3.11.

## Quickstart

```bash
jellycell init my-project
cd my-project

# (once per repo) drop AGENTS.md + CLAUDE.md so agentic tools read jellycell's guide
jellycell prompt --write

jellycell new tour                  # scaffold notebooks/tour.py
# edit in your editor of choice
jellycell run notebooks/tour.py     # first run executes; cached afterward
jellycell render notebooks/tour.py  # writes site/tour.html
jellycell view                      # live viewer (needs [server] extra)
```

## Project layout

```
my-project/
├── jellycell.toml          # project config
├── notebooks/              # .py notebooks (jupytext percent format)
├── data/                   # input data, read by jc.load
├── artifacts/              # outputs written by jc.save / jc.figure / jc.table
├── site/                   # rendered HTML (jellycell render)
├── manuscripts/            # narrative docs + tearsheets (markdown, committed)
└── .jellycell/cache/       # content-addressed cache (gitignored)
```

**Monorepo**: one repo can hold several jellycell projects side by side. Put a single `AGENTS.md` at the **repo root** (not per project) — `jellycell prompt --write` detects outer AGENTS.md files and refuses to scatter inner duplicates without `--force`. See [project-layout.md](https://github.com/random-walks/jellycell/blob/main/docs/project-layout.md#multi-project--monorepo-pattern).

## Notebook format

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas", "matplotlib"]
#
# [tool.jellycell]
# timeout_seconds = 1800
# ///

# %% [markdown]
# # Tour
# One-paragraph description of what this notebook does.

# %% tags=["jc.load", "name=raw"]
import pandas as pd
raw = pd.read_csv("data/sales.csv")

# %% tags=["jc.step", "name=summary", "deps=raw"]
import jellycell.api as jc
summary = raw.describe()
jc.save(summary, "artifacts/summary.json")
jc.table(summary, caption="Sales summary")
```

- **PEP-723 script header**: `requires-python` + `dependencies` + optional `[tool.jellycell]` file-scope overrides (allow-listed keys: `project.name`, `run.kernel`, `run.timeout_seconds`).
- **Cell tags**: `# %% tags=[...]` markers carry `cell-id`, `name`, `kind`, `deps`, `timeout_s`. Parsed by `jellycell.format`.
- **Cell kinds** (declared via `kind=`): `load`, `setup`, `step`, `figure`, `table`. Drives lint and tearsheet rendering.
- **`tearsheet` tag** (1.3.5+): orthogonal to kind. Drop it on a cell (`tags=["jc.figure", "tearsheet"]`) or an artifact (`jc.save(x, path, tags=["tearsheet"])`) to filter which artifacts inline into `jellycell export tearsheet`. Any `tearsheet` tag in a notebook auto-enables filtering; no tags = every artifact inlined (old behavior).

## The `jc.*` API

`import jellycell.api as jc`. Works inside a run (reads the live `RunContext`) and as a plain script (standalone mode).

| Call | Purpose |
| --- | --- |
| `jc.load(path)` | Read input; registers an implicit dep edge on the producing cell via the artifact lineage index |
| `jc.save(obj, path, caption=..., notes=..., tags=[...])` | Write an artifact; metadata lands on the `ArtifactRecord` in the cell manifest |
| `jc.figure(path, fig=..., caption=..., notes=..., tags=[...])` | Save a matplotlib figure, or with no `fig=` and an existing file at `path`, register it without re-encoding (1.3.2+) |
| `jc.table(df, caption=..., notes=..., tags=[...])` | Save a dataframe as markdown or parquet (layout-driven) |
| `jc.deps("a", "b")` | Runtime-declared deps; AST-walked into the current cell's cache key |
| `jc.cache` | Decorator that memoizes function calls via the content-addressed store |
| `jc.path("name")` | Resolve an artifact path by producer name |
| `jc.ctx` | Access the current `RunContext` (cell id, cache key, project paths) |

## CLI commands

- `jellycell init <path>` — scaffold a project.
- `jellycell new <name>` — scaffold a notebook from the starter template.
- `jellycell run <nb> [-m "msg"] [--force]` — execute end-to-end with caching; journal-aware.
- `jellycell lint [--fix]` — policy-gated lint (layout, PEP-723 position, artifact paths, declared deps, cell output size).
- `jellycell render [nb] [--standalone]` — build static HTML under `site/`.
- `jellycell view` — live Starlette + SSE viewer (needs `[server]` extra).
- `jellycell cache {list|prune|clear|rebuild-index}` — cache admin.
- `jellycell export {ipynb|md|tearsheet} <nb>` — derived outputs.
- `jellycell checkpoint {create|list|restore}` — reproducible `.tar.gz` snapshots.
- `jellycell prompt [--write [DIR]]` — agent guide (stdout or `AGENTS.md` + `CLAUDE.md`).

Every command supports `--json` for machine-readable output carrying `schema_version: 1`.

## Stability contracts (§10)

Three cross-cutting promises, each gated by a major version bump:

1. **§10.1 `--json` schemas**. Every CLI command's JSON output has a pydantic model with `schema_version: int`. Adding optional fields is additive (minor); renaming / removing / re-typing is breaking (major + `schema_version` bump).
2. **§10.2 Cache key algorithm**. `sha256(normalized_source, sorted_dep_keys, env_hash, MINOR_VERSION)`. Any change — normalization, inputs, composition — forces `MINOR_VERSION` bump and a major release (entire cache invalidates).
3. **§10.3 Agent guide content**. Bytes emitted by `jellycell prompt` are stable across patches. Additive content is minor; breaking edits are major.

Full ceremony: [docs/reference/contracts.md](https://github.com/random-walks/jellycell/blob/main/docs/reference/contracts.md).

## Architecture — 8-layer dependency order

```
CLI → Server → Render → Run → API → Cache → Format → Paths+Config
```

Upper layers import only from lower. The `cache/` layer must not import from `run/`, `render/`, or `server/`. Full piggyback map + subpackage responsibilities: [docs/reference/architecture.md](https://github.com/random-walks/jellycell/blob/main/docs/reference/architecture.md).

## Piggyback policy

jellycell's value is composition. We depend on `jupytext`, `jupyter-client`, `nbformat`, `nbconvert` (output helpers only), `diskcache`, `markdown-it-py` + MyST plugins, `jinja2`, `starlette` + `watchfiles` + `sse-starlette`, `typer`, `pydantic`. We own the tag vocabulary, cache key derivation, manifest format, per-cell orchestration, page shell, dep graph, and agent guide.

Before writing new code, check [docs/reference/architecture.md](https://github.com/random-walks/jellycell/blob/main/docs/reference/architecture.md) — the piggyback map lists every delegated responsibility.

## Idiomatic patterns

- **Name your cells**: `tags=["jc.step", "name=summary"]`. Named cells produce paths you can reference from `jc.load` / `jc.path` and appear in tearsheet navigation.
- **Declare deps explicitly**: `deps=raw,config` in tags, or `jc.deps("raw", "config")` inline. Implicit dep edges from `jc.load(path)` still work; explicit wins on readability.
- **Artifacts**: prefer explicit paths for shared outputs (`jc.save(x, "artifacts/key.json")`); use `jc.figure()` / `jc.table()` with `caption="..."` for path-less saves driven by `[artifacts] layout`.
- **Captions matter**: caption / notes / tags on `jc.save` / `jc.figure` / `jc.table` flow into the tearsheet and the analysis journal.
- **One AGENTS.md per repo**: not per jellycell project. `jellycell init` detects outer coverage; `jellycell prompt --write` warns before scattering inner overrides.
- **Commit the journal** (`manuscripts/journal.md`) — reviewers (and you in six months) use it to answer "why did the numbers change?"
- **Git-ignore** `.jellycell/` (cache) and `site/` (HTML); commit `notebooks/`, `data/` (small), `artifacts/` (outputs worth reviewing), `jellycell.toml`, `manuscripts/`.

## Example projects

The `examples/` folder in the repo has five fully-worked projects, each with a README, jellycell.toml, notebooks, and hand-authored manuscripts:

- `minimal/` — bare-bones first touch.
- `demo/` — analytics walkthrough (conversion numbers).
- `paper/` — a paper draft with tearsheets + hand-authored writeup.
- `timeseries/` — decomposition + forecasting with named cells + cross-notebook deps.
- `ml-experiment/` — training run with model card.
- `large-data/` — `[artifacts] layout = "by_notebook"` + `max_committed_size_mb` workflow (commit the digest, git-ignore the bulk).

## Links for deeper reading

- [Getting started](https://jellycell.readthedocs.io/en/latest/getting-started.html)
- [File format](https://jellycell.readthedocs.io/en/latest/file-format.html)
- [Project layout](https://jellycell.readthedocs.io/en/latest/project-layout.html)
- [CLI reference](https://jellycell.readthedocs.io/en/latest/cli-reference.html)
- [Agent guide (§10.3)](https://jellycell.readthedocs.io/en/latest/agent-guide.html)
- [Architecture reference](https://jellycell.readthedocs.io/en/latest/reference/architecture.html)
- [§10 Contracts](https://jellycell.readthedocs.io/en/latest/reference/contracts.html)
