# CLAUDE.md — jellycell

One-screen brief for agents working in this repo. Full context: [`docs/spec/v0.md`](docs/spec/v0.md).

## What this is

`jellycell` is a reproducible-analysis notebook tool: plain-text `.py` notebooks (jupytext percent format), content-addressed cell output cache, live HTML viewer. The **point of the project is composition** — we piggyback on jupytext, nbformat, jupyter-client, diskcache, nbconvert, starlette. Spec §1 has the full piggyback map; **read it before writing parsing / caching / rendering / file-watching code**.

## Invariants — DO NOT CHANGE SILENTLY

Three contracts (spec §10). Touching any of them is a deliberate ceremony.

1. **`--json` output schemas.** Every command's JSON output carries `schema_version: 1`. Adding/removing/renaming a field breaks the contract → bump `schema_version` in the owning pydantic model AND call it out in the PR description.
2. **Cache key algorithm.** Lives in `src/jellycell/cache/hashing.py`. Any change to normalization, inputs, or composition of the hash requires bumping `MINOR_VERSION` in `src/jellycell/_version.py` so every cache invalidates cleanly. Regression snapshot: `tests/unit/test_hashing.py`. Never change silently.
3. **Agent guide content.** What `jellycell prompt` emits (Phase 6; `src/jellycell/cli/commands/prompt.py`). Stable across patch versions; changes go in minor releases with a `CHANGELOG.md` entry.

Before editing `cache/hashing.py`, `_version.py`, `cli/commands/prompt.py`, or any pydantic model with a `schema_version` field — run `/spec-check` on your diff.

## 8-layer dependency order (spec §2)

Upper depends only on lower. `cache/` must never import from `run/`, `render/`, `server/`. Break this and the refactor radius explodes.

```
CLI → Server → Render → Run → API → Cache → Format → Paths+Config
```

## Phase budgets (spec §8)

Phases are an **implementation-order artifact**, not a release plan — all six shipped together as `v1.0.0`. The per-phase src budgets are retained because they are still useful as scope-creep signals when extending one area.

| Phase | src budget | Purpose                                  |
| ----- | ---------- | ---------------------------------------- |
| 0     | 3          | Skeleton                                 |
| 1     | 13         | Format, config, init, lint               |
| 2     | 13         | Cache, run, API                          |
| 3     | 10         | Render (HTML)                            |
| 4     | 4          | Live viewer                              |
| 5     | 3          | Export (ipynb/md)                        |
| 6     | +2         | Agent surface                            |

**If a phase's src count creeps past its budget while you're extending it, cut back — do not raise the ceiling.** Drift is a scope-creep signal. Run `/phase-status` to check.

## Piggyback reminders (spec §1)

Before writing new code, ask: is this already done by one of these?

- **jupytext** — `.py`/`.md` ↔ notebook IR. Don't reparse percent format.
- **nbformat** — `NotebookNode` for I/O and validation of the ipynb format.
- **jupyter-client** — kernel subprocess, message protocol. Don't roll a REPL.
- **diskcache** — content-addressable blob store. Don't write your own on-disk LRU.
- **nbconvert** — mime bundle → safe HTML (use the *output helpers*, not the full HTMLExporter).
- **markdown-it-py + mdit-py-plugins** — markdown rendering.
- **watchfiles** — file-system watching with debouncing.
- **sse-starlette** — SSE transport.

## Dev commands

```
make dev              # uv sync + pre-commit install
make test             # full pytest suite
make test-unit        # unit tests only (fast)
make lint             # ruff + mypy
make docs             # sphinx-autobuild, live at :8001
make docs-build       # sphinx-build -W (CI mirror)
make preview          # Phase 3+ placeholder
make release-check    # dry-run build + version print
```

## Agent surface

`jellycell prompt` emits the canonical agent guide — a single markdown doc covering layout, format, tags, API, and CLI reference. Content is **spec §10.3 stability contract**. Start by calling this in any new jellycell project.

## Versioning

Patch bumps are cheap — prefer frequent small releases over feature-batching. Full policy in [docs/development/releasing.md](docs/development/releasing.md). When finishing a user-visible change, invoke the `release-bump` skill or run `/bump` to move `[Unreleased]` into a numbered entry.

## Before merging

- `make lint && make test && make docs-build` all green.
- Docstrings on every new public function (ruff D100–D103 enforced).
- PR template has "Invariant touched?" filled in.
- Phase budget respected (`/phase-status` clean).
