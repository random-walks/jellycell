# Changelog

All notable changes to jellycell follow the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format, and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Pre-1.0: minor versions may include breaking changes; the spec version (see `_version.MINOR_VERSION`) is what guards cache invalidation.

## [Unreleased]

## [0.2.0] — 2026-04-18

Comprehensive close-out of v0.1.0 deferred items and loose contracts. **This release bumps `MINOR_VERSION` 1 → 2; every existing cache entry invalidates on first run.** The invalidation is one-shot and intentional — see the cache-key changes below.

### Added
- **`jc.cache`** now actually memoizes via the content-addressed cache store (was: identity decorator). Keys on `(qualname, source, pickled args)`. Standalone mode is unchanged passthrough.
- **`jc.load()` registers an implicit dep edge** on the producing cell (via new artifact lineage index). Cross-notebook dataflow now invalidates correctly without hand-written `deps=` tags.
- **Static AST walk for `jc.deps("a", "b")`.** The runner parses `jc.deps(...)` out of cell source before executing, so declared deps enter the cache key (was: runtime-only, too late to affect the current cell's key).
- **Lockfile-based `env_hash`.** Prefers `uv.lock` / `poetry.lock` bytes over PEP-723 dependency list. Two environments resolving to different concrete versions no longer share a cache.
- **Artifact lineage reverse index** (`CacheIndex.find_producer`). Surfaces "which cell produced this file?" via the SQLite index; consumed by `jc.load` (dep registration) and `jc.path("name")` (artifact-by-name lookup).
- **Three real lint rules** previously stubbed:
  - `enforce-artifact-paths` — `jc.save/figure/table` must write under `paths.artifacts`.
  - `enforce-declared-deps` — cells using `jc.load` from another cell's artifact must declare the dep.
  - `warn-on-large-cell-output` — cached cells exceeding the size threshold get a non-fixable warning.
- **`KernelPool`** reuses a kernel across multiple `Runner.run()` calls (for `render_all` + batch scripts). Opt-in via `Runner(project, kernel_pool=pool)`.
- **`jellycell cache prune`** — remove cached entries by `--older-than` duration or `--keep-last N` per notebook. `--dry-run` lists without deleting. Manifests only in this release; ref-counted blob GC lands in a follow-up.
- **PEP-723 `[tool.jellycell]` overrides are applied at runtime** (`Project.with_overrides`). Supported keys: `project.name`, `run.kernel`, `run.timeout_seconds`. Unknown keys raise `UnknownOverrideKeyError`.
- **Wall-clock kernel timeout.** `Kernel.execute` now uses `time.monotonic()` for a true deadline (was: per-iopub-chunk poll that a slow-drip cell could outlast).
- **Cell error tracebacks surface in `jellycell run` output.** The run-report table is followed by a formatted traceback block for each errored cell.
- **Security warning on non-loopback `jellycell view`.** Binding `--host 0.0.0.0` (or any non-`127.0.0.1`/`localhost`/`::1` address) prints a stderr banner noting the exposure.
- **Mixed cache-hit/miss note** at end of `jellycell run` when a single run touches both paths — flags the classic in-memory-dataflow foot-gun.
- **Unified asset layout** (`reports/_assets/`). Static render + live server share one content-addressed asset tree; the old per-notebook `reports/<stem>/_assets/` subdirs are gone, and the server no longer forces `standalone=True` to work around the old mount gap.
- **New tests**: `test_pep723_overrides.py`, `test_static_deps.py`, `test_function_cache.py`, `test_server_sse_e2e.py` (real uvicorn + broker → HTTP), `test_render_parity.py` (static vs. server byte-equal), `test_kernel_timeout.py`, `test_kernel_pool.py`, `tests/examples/test_examples_run.py` (CI runs every example notebook), plus regression snapshots for `jellycell prompt` (§10.3) and every `--json` command (§10.1).
- **CI `examples` job** runs `pytest tests/examples/` on ubuntu/py3.12.

### Changed
- **Cache key inputs expanded** (§10.2 break). Deps from `jc.load` artifact lineage + AST-walked `jc.deps(...)` now enter the key. Lockfile bytes feed `env_hash` when present.
- **Error-status manifests are no longer cache hits.** Transient failures re-execute on retry (was: cached error was returned silently).
- **`.ipynb` export `execution_count`** now reflects the *last* `execute_result` (was: first). Matches nbformat convention.
- **Server drops `standalone=True` workaround.** Live viewer now serves `_assets/*.png` via a real `/_assets/` mount; HTML is byte-identical to the static-render output.
- **`phase-budget` skill** rewritten with accurate per-phase counts + explicit instruction to prefer `/phase-status` over the table.

### Contracts (§10)
- **§10.2 cache-key break:** `MINOR_VERSION` bumped 1 → 2. `tests/unit/test_hashing.py` regression snapshot regenerated.
- **§10.1 JSON schemas:** now pinned by `tests/integration/test_json_schemas.py` (shape snapshots per command). Adding/removing/renaming a field fails the snapshot.
- **§10.3 agent guide:** content updated (new `jc.cache` / `jc.load dep`, dataflow guidance, lockfile env_hash, cache prune). `jellycell prompt` output pinned by `tests/unit/test_prompt_snapshot.py`.

### Notes
- **Ref-counted blob GC for `cache prune`** is deferred. Current prune removes manifests only; blobs linger but diskcache deduplicates content-addressed storage anyway.
- **`jc.cache` arg hashing** uses pickle. Unpicklable inputs raise clearly at call time; a JSON-default fallback can come later.

## [0.1.0] — 2026-04-17

First real release. All phases of the v0 spec shipped.

### Added
- **Phase 3: Render.** `jellycell render` produces self-contained HTML reports under `reports/`. Supports `--standalone` to base64-inline images. Templates use jinja2; code highlighting via Pygments; markdown via markdown-it-py + MyST plugins.
- **Phase 4: Live viewer.** `jellycell view` serves a Starlette + SSE app with live reload on file changes. Routes: `/`, `/nb/<stem>`, `/artifacts/<...>`, `/api/state.json`, `/events`. Read-only. Requires the `[server]` extra.
- **Phase 5: Export.** `jellycell export ipynb <nb>` produces a runnable `.ipynb` with cached outputs reattached. `jellycell export md <nb>` produces MyST markdown for Sphinx / Jupyter Book integration.
- **Phase 6: Agent surface.** `jellycell prompt` emits the canonical agent guide — spec §10.3 contract. `jellycell new <name>` scaffolds a notebook from the starter template.
- Docs: `getting-started.md`, `file-format.md`, `project-layout.md`, `cli-reference.md`, `agent-guide.md` are all authoritative. CLI reference auto-generated via `sphinxcontrib-typer`.
- Examples: `examples/minimal/` (smallest-possible project) and `examples/demo/` (tour of cell types + `jc.*` API). `.claude/launch.json` points Claude Code's preview server at the demo.

### Notes
- Three §10 contracts locked: cache key algorithm (`_version.MINOR_VERSION`), `--json` schemas (`schema_version: 1`), agent guide content.
- Future minor releases: more lint rules (`enforce_artifact_paths`, `enforce_declared_deps`, `warn_on_large_cell_output` — config gates exist; implementations deferred).

## [0.0.2] — 2026-04-17

### Added
- `jellycell run <notebook>` — execute a notebook via a subprocess Jupyter kernel, with per-cell content-addressed caching.
- `jc.*` API (`save`, `figure`, `table`, `load`, `path`, `deps`, `cache`, `ctx`) — works inside a run and as a plain script (standalone mode).
- `jellycell cache list`, `jellycell cache clear`, `jellycell cache rebuild-index`.
- Cell execution manifests on disk (`.jellycell/cache/manifests/*.json`) plus SQLite catalogue accelerator (`state.db`).
- Cache-key spec §10.2 locked by a regression snapshot (`tests/unit/test_hashing.py`).
- Integration tests exercising real Jupyter kernels.

### Changed
- `src/jellycell/__main__.py` now delegates to `jellycell.cli.app:app`.
- `[project.scripts]` re-enabled in `pyproject.toml` now that `jellycell.cli.app` exists.

## [0.0.1] — 2026-04-17

### Added
- Package skeleton, CI, and PyPI trusted-publisher release pipeline.
- Sphinx docs on ReadTheDocs with frozen v0 spec at `docs/spec/v0.md`.
- Claude Code project infrastructure: CLAUDE.md, slash commands, subagent, skills for spec-invariant enforcement.

### Notes
- This release is scaffolding only. No user-facing commands work yet.
- PyPI name is reserved; trusted publisher flow is verified end-to-end.

[Unreleased]: https://github.com/random-walks/jellycell/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/random-walks/jellycell/releases/tag/v0.2.0
[0.1.0]: https://github.com/random-walks/jellycell/releases/tag/v0.1.0
[0.0.2]: https://github.com/random-walks/jellycell/releases/tag/v0.0.2
[0.0.1]: https://github.com/random-walks/jellycell/releases/tag/v0.0.1
