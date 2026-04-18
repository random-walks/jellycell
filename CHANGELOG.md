# Changelog

All notable changes to jellycell follow the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format, and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versioning policy: **patch bumps are cheap**. See [docs/development/releasing.md](docs/development/releasing.md) for the full policy and the three §10 contracts that govern major bumps.

## [Unreleased]

## [1.0.0] — 2026-04-18

First public release.

### Features — notebook format

- **Plain-text `.py` notebooks** in jupytext percent format with PEP-723 headers. Jellycell strip-and-re-inserts the PEP-723 block so jupytext's round-trip is byte-exact.
- **Tag vocabulary** on `# %%` markers: `cell-id`, `name`, `kind`, `deps`, `timeout_s`. Parsed by `jellycell.format`; registry lives in `format/tags.py`.
- **`[tool.jellycell]` file-scope overrides** inside the PEP-723 block. Allow-listed keys: `project.name`, `run.kernel`, `run.timeout_seconds`. Unknown keys raise `UnknownOverrideKeyError` — no silent typos.

### Features — cache + run

- **Content-addressed per-cell cache.** Key = `sha256(source, sorted_dep_keys, env_hash, MINOR_VERSION)`. Stored as JSON manifests + diskcache blobs with a SQLite catalogue accelerator.
- **`jellycell run`** executes notebooks via a subprocess Jupyter kernel. Cache-hit cells skip execution; cache-miss cells stream outputs to the cache and write artifacts to `artifacts/`.
- **`jc.*` runtime API**: `save`, `load`, `figure`, `table`, `path`, `deps`, `cache`, `ctx`. Works inside a run (reads `RunContext`) and as a plain script (standalone mode).
- **`jc.cache` decorator** memoizes function calls via the same content-addressed store. Keys on `(qualname, normalized source, pickled args)`. Standalone mode is identity passthrough.
- **`jc.load()` registers an implicit dep edge** on the producing cell via the artifact lineage index — cross-notebook dataflow invalidates correctly without hand-written `deps=` tags.
- **Static AST walk for `jc.deps("a", "b")`.** The runner parses `jc.deps(...)` out of cell source *before* executing, so runtime-declared deps enter the current cell's cache key (not just downstream cells').
- **Lockfile-aware `env_hash`.** Prefers `uv.lock` / `poetry.lock` bytes over the PEP-723 dependency list. Two environments that resolve to different concrete versions no longer share a cache.
- **Artifact lineage reverse index** (`CacheIndex.find_producer`): "which cell produced this file?" via SQLite. Consumed by `jc.load` dep registration and `jc.path("name")` lookup.
- **Wall-clock kernel timeout.** `Kernel.execute` uses `time.monotonic()` for a true deadline — slow-drip output no longer outruns the cap.
- **`KernelPool`** reuses a single kernel across multiple `Runner.run()` calls for batch scripts and `render_all`. Opt-in via `Runner(project, kernel_pool=pool)`. Default stays fresh-per-run for isolation.
- **`jellycell cache`** subcommands: `list`, `clear`, `prune` (`--older-than` / `--keep-last` / `--dry-run`), `rebuild-index`.

### Features — lint + config

- **`jellycell lint`** with fixers: `layout`, `pep723-position`, `enforce-artifact-paths`, `enforce-declared-deps`, `warn-on-large-cell-output`.
- **`jellycell init`** scaffolds a project with `jellycell.toml`, the canonical directory layout, and a starter notebook.
- **`jellycell new <name>`** scaffolds a new notebook from the starter template.

### Features — render + view

- **`jellycell render`** produces self-contained HTML under `reports/`. Templates use jinja2; code highlighting via Pygments; markdown via markdown-it-py + MyST plugins.
- **`jellycell view`** (needs `[server]` extra) serves a Starlette + SSE app with live-reload on file changes. Routes: `/`, `/nb/<stem>`, `/artifacts/<...>`, `/_assets/<...>`, `/api/state.json`, `/events`. Read-only.
- **Unified asset layout** (`reports/_assets/`): static render and the live server share one content-addressed asset tree. HTML is byte-identical across both paths.
- **Security warning on non-loopback `jellycell view`.** Binding `--host 0.0.0.0` (or any non-`127.0.0.1`/`localhost`/`::1` host) prints a banner about the exposure.

### Features — export

- **`jellycell export ipynb <nb>`** produces a runnable `.ipynb` with cached outputs reattached. `execution_count` matches nbformat convention (last `execute_result`, not first).
- **`jellycell export md <nb>`** produces MyST markdown for Sphinx / Jupyter Book integration.
- **`jellycell export tearsheet <nb>`** writes a curated markdown tearsheet to `manuscripts/<stem>.md` by default (override with `-o PATH`). Pulls markdown cell prose, inlines image artifacts via relative paths, and flattens JSON summaries into two-column tables. Safe to commit — GitHub renders it inline. Example tearsheets ship under `examples/*/manuscripts/`.

### Features — agent surface

- **`jellycell prompt`** emits the canonical agent guide — a single markdown doc covering layout, format, tags, API, and CLI reference. Content is the §10.3 stability contract; pinned by a regression snapshot.
- Every CLI command supports `--json` with a versioned schema (§10.1). Shapes pinned by per-command regression snapshots.

### Docs + infra

- Docs on Read the Docs: getting-started, file-format, project-layout, cli-reference, agent-guide, plus the frozen v0 spec and dev guides.
- Examples: `minimal/`, `demo/`, `timeseries/`. CI runs every example notebook end-to-end.
- Claude Code infra: CLAUDE.md, slash commands (`/spec-check`, `/phase-status`), subagents, skills (`spec-invariant`, `phase-budget`, `piggyback-first`).
- Release pipeline on PyPI via trusted publisher (OIDC).

### Contracts locked (§10)

1. **`--json` schemas** (`schema_version: 1`). Pinned by `tests/integration/test_json_schemas.py`.
2. **Cache key algorithm** (`MINOR_VERSION = 1`). Pinned by `tests/unit/test_hashing.py`.
3. **Agent guide content** (`jellycell prompt`). Pinned by `tests/unit/test_prompt_snapshot.py`.

Each contract has a documented ceremony for changes — see [docs/development/releasing.md](docs/development/releasing.md) and CLAUDE.md.

### Known limitations

- `cache prune` removes manifests but not blobs. diskcache deduplicates content-addressed storage so disk impact is small; a ref-counted blob GC lands in a future release.
- `jc.cache` argument hashing uses pickle. Unpicklable inputs raise clearly at call time; a JSON-default fallback can come later.

[Unreleased]: https://github.com/random-walks/jellycell/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/random-walks/jellycell/releases/tag/v1.0.0
