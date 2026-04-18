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
- **`jellycell export tearsheet <nb>`** writes a curated markdown tearsheet to `manuscripts/tearsheets/<stem>.md` by default (override with `-o PATH`). The `tearsheets/` subfolder convention keeps auto-generated output separate from hand-authored writeups (paper drafts, memos, thesis chapters) that live at the root of `manuscripts/`. Pulls markdown cell prose, inlines image artifacts via relative paths, and flattens JSON summaries into two-column tables. Header block labels the file as a tearsheet with a link to the source notebook, to `reports/<stem>.html` when it exists, and the last-run timestamp. Safe to commit — GitHub renders it inline. Example tearsheets ship under `examples/*/manuscripts/tearsheets/`.

### Features — agent surface

- **`jellycell prompt`** emits the canonical agent guide — a single markdown doc covering layout, format, tags, API, and CLI reference. Content is the §10.3 stability contract; pinned by a regression snapshot.
- Every CLI command supports `--json` with a versioned schema (§10.1). Shapes pinned by per-command regression snapshots.

### Docs + infra

- Docs on Read the Docs: getting-started, file-format, project-layout, cli-reference, agent-guide, plus the frozen v0 spec and dev guides.
- Examples: `minimal/`, `demo/`, `timeseries/`. CI runs every example notebook end-to-end.
- Claude Code infra: CLAUDE.md, slash commands (`/spec-check`, `/phase-status`), subagents, skills (`spec-invariant`, `phase-budget`, `piggyback-first`).
- Release pipeline on PyPI via trusted publisher (OIDC).

### Features — live viewer lifts (manuscripts + journal + tearsheet nav)

- **Manuscript previewer**: new `/manuscripts/` landing page + dynamic
  `/manuscripts/<path>.md` route serves any markdown under
  `manuscripts/` through the project's template stack. Authored
  writeups, auto-generated tearsheets, and the journal all render
  in-browser with the same chrome as notebook pages.
- **Journal viewer**: `/journal` is a first-class route aliasing the
  configured journal file. Live-reloads on every `jellycell run`
  through the existing watchfiles → SSE pipeline so the trajectory
  appears in-browser as it's written.
- **Tearsheet ↔ notebook cross-links**: each notebook HTML page now
  shows a `Tearsheet →` button when `manuscripts/tearsheets/<stem>.md`
  exists; tearsheet pages show a matching `Notebook →` link when the
  source notebook is present. One click to flip between source and
  curated summary.
- **Per-tearsheet prev/next navigation**: when browsing a tearsheet,
  the header carries `← previous / next →` links to the adjacent
  tearsheets in alphabetical order. Authored writeups don't get the
  prev/next pair since they're standalone documents.
- **Sidebar reorganization on manuscript pages**: three groups
  (Authored / Tearsheets / Log) with the active page highlighted.
- **Targeted SSE reloads**: `manuscripts/**/*.md` edits now publish a
  `ReloadEvent` for the specific page (`/manuscripts/<path>` or
  `/journal`) instead of broadly reloading the index.
- **`/api/state.json`** gains a `manuscripts` payload
  (authored + tearsheets + journal catalog). Additive — no
  `schema_version` bump.

### Features — artifact metadata + journal + checkpoint

- **Artifact metadata via `jc.*` kwargs** — `jc.save`, `jc.figure`, and
  `jc.table` accept optional `caption="..."`, `notes="..."`, `tags=[...]`.
  Captured in the `ArtifactRecord` inside the cell manifest (additive
  optional fields; §10.1 safe — no `schema_version` bump, no
  `MINOR_VERSION` bump). Tearsheets render caption as the figure /
  table heading, notes as an italic subcaption, tags as a searchable
  line below.
- **Analysis journal** — `manuscripts/journal.md` gets one append-only
  section per `jellycell run`: timestamp, notebook, cell counts,
  duration, new artifacts (with captions), large-artifact warnings,
  any errors, and the optional `-m "..."` message. Default-on (opt-out
  via `[journal] enabled = false`). Append-only from jellycell's side
  so hand-edited commentary survives future runs. New `-m / --message`
  flag on `jellycell run`.
- **`jellycell checkpoint`** — reproducible `.tar.gz` snapshots with
  `create`, `list`, `restore` subcommands. Archives notebooks, data,
  artifacts, reports, manuscripts, `jellycell.toml`, and
  `.jellycell/cache/`. Junk dirs (`__pycache__`, `.venv`, `.git`, etc.)
  are skipped. **Restore is safe by default**: lands in a new sibling
  directory (`<project>-restored-<name>/`) so the live project is
  never touched. `--into PATH` lets you pick a location; `--force` is
  required to merge into a non-empty target.
- **Contracts doc clarification** — [reference/contracts](docs/reference/contracts.md)
  now makes explicit that additive optional fields on manifest schemas
  are backwards-compatible (no `MINOR_VERSION` bump) so long as
  defaults preserve old-manifest deserialization.

### Features — artifact layout + large-file handling

- **`[artifacts]` config section** in `jellycell.toml`:
  - **`layout`** (`"flat"` / `"by_notebook"` / `"by_cell"`, default
    `"flat"`): controls where path-less `jc.figure()` / `jc.table()`
    writes. `"by_cell"` makes every artifact path name its producer
    (`artifacts/<notebook>/<cell>/<name>.<ext>`) — agent-friendly for
    "what generated what" lookups. Explicit `jc.save(x, "...")` paths
    always win, so existing notebooks keep working unchanged.
  - **`max_committed_size_mb`** (default `50`): post-run soft threshold.
    `jellycell run` flags any single artifact above the limit with a
    `.gitignore` / Git LFS reminder. Set to `0` to disable.
- **New `large-data` example** under `examples/large-data/`
  demonstrates the full pattern: `[artifacts] layout = "by_notebook"`,
  low `max_committed_size_mb`, a tiny committed `headline.json` digest
  next to a git-ignored generated parquet, and a reproducible seed so
  reviewers regenerate locally.
- **Additive `RunReport.large_artifacts` field** — a list of
  `LargeArtifactWarning` entries surfaced to both the JSON and rich
  outputs of `jellycell run`. §10.1 additive (no `schema_version` bump).

### Examples — READMEs + hand-authored manuscripts

Every example now ships a top-level `README.md` with bootstrap commands
(both `uv` and `pip`), a layout diagram, and "what this example shows."
Every example's `manuscripts/` folder carries a hand-authored
`.md` alongside the auto-generated tearsheet(s):

- `minimal/manuscripts/notes.md` — first-run reflection.
- `demo/manuscripts/analysis.md` — analyst's read on the conversion numbers.
- `paper/manuscripts/paper.md` — paper draft (already existed; now cross-linked).
- `timeseries/manuscripts/findings.md` — interpretation of decomposition + forecast.
- `ml-experiment/manuscripts/model-card.md` — training-run log.
- `large-data/manuscripts/data-notes.md` — reproducibility protocol.

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
