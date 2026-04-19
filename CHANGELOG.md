# Changelog

All notable changes to jellycell follow the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format, and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versioning policy: **patch bumps are cheap**. See [docs/development/releasing.md](docs/development/releasing.md) for the full policy and the three §10 contracts that govern major bumps.

## [Unreleased]

## [1.1.2] — 2026-04-18

### Docs — Context7 config restore

- **`context7.json`** restored to the scoped-ingest config promised by
  1.1.1 — `folders`, `excludeFolders` (skipping `.claude`, `tests`,
  `docs/development`, `docs/spec`, etc.), `excludeFiles`, `rules`,
  `previousVersions`. 1.1.1 had to minimize the file to just
  `{url, public_key}` for Context7's library-claim verification
  (strict `additionalProperties: false` on the claim endpoint);
  after claim succeeded, the claim fields are no longer needed in
  the committed file.

## [1.1.1] — 2026-04-18

Context7 ingestion hygiene — separate dev-facing from consumer-facing.

### Docs — Context7 scoping

- **Hand-curated [`context7.md`](context7.md)** at repo root. Single
  agent-focused primer covering install, quickstart, project layout,
  notebook format, `jc.*` API, CLI surface, §10 contracts, and
  architecture — with deep-link URLs to the RTD-hosted full versions.
  Context7 was auto-generating one with Claude on each re-ingest; the
  hand-curated file takes precedence and keeps the summary stable.
- **[`context7.json`](context7.json) scoping**:
  - `folders: ["docs/", "examples/"]` (was `["docs/"]`) — examples are
    consumer-facing patterns and should be indexed.
  - `excludeFolders` now covers `.claude`, `.github`, `scripts`,
    `tests`, `docs/development`, `docs/spec` — dev-facing project
    infrastructure that Context7 was indexing as if it were user
    docs (the prior ingest surfaced 4 `.claude/skills/**/SKILL.md`
    files meant for jellycell contributors, not downstream consumers).
  - `excludeFiles: ["CLAUDE.md", "CONTRIBUTING.md", "CHANGELOG.md"]` —
    root-level dev-facing files.
  - `rules: [...]` — five short agent-guidance statements surfacing
    the §10 contracts, the agent-guide entry point, and the monorepo
    AGENTS.md policy.

### Contracts (§10)

- §10.1, §10.2, §10.3: all unchanged. Docs-only release.

## [1.1.0] — 2026-04-18

Agentic-IDE reach + AI-friendly docs delivery. No code breaks anything
under v1.0; §10.3 stdout bytes are preserved (no snapshot regen).

### Features — agent surface

- **`jellycell prompt --write [DIR]`** drops `AGENTS.md` + a 1-line
  `CLAUDE.md` stub into the target directory (defaults to cwd).
  `AGENTS.md` is the full `jellycell prompt` content with the MyST
  `:::{important}` directive rewritten as a GitHub-rendered blockquote;
  `CLAUDE.md` points at `AGENTS.md` so Claude Code picks it up via its
  own convention. Single command, every AGENTS.md-native tool (Cursor,
  Codex, GitHub Copilot, Aider, Zed, Warp, Windsurf, Junie, RooCode,
  Gemini CLI, …) now sees jellycell's §10.3 guide. `--force` overwrites
  existing files; `--agents-only` skips the `CLAUDE.md` stub.
- **Monorepo-safe scatter prevention**: `jellycell prompt --write`
  walks ancestors for an outer `AGENTS.md` (stops at `.git/`, `$HOME`,
  or filesystem root) and refuses to write a duplicate inside unless
  `--force` is passed. Agentic tools compose nested AGENTS.md files —
  one file at the repo root covers every jellycell project underneath.
- **`jellycell init` AGENTS.md hint**: end-of-init, `jellycell init`
  detects whether an outer `AGENTS.md` already covers the target and
  prints either `✓ agent guide detected at ../AGENTS.md` or a tip
  showing how to add one via `jellycell prompt --write`. Advisory
  only — `init` never writes `AGENTS.md` itself, no scaffold pollution.
  `InitReport.agents_md_hint: str | None` exposes the detected path in
  `--json` mode (§10.1 additive; no `schema_version` bump).
- **`PromptWriteReport`** pydantic model for `jellycell prompt --write
  --json` with `schema_version: 1`, `written`, `skipped`,
  `outer_agents_md`. Pinned by `tests/integration/test_json_schemas.py`.

### Docs — AI-friendly delivery

- **`sphinx-llms-txt` integration**. The Sphinx build now emits
  `docs/_build/html/llms.txt` (curated index of all project pages) and
  `llms-full.txt` (full markdown concat). Read the Docs auto-serves
  them at `https://jellycell.readthedocs.io/llms.txt` and
  `/llms-full.txt` — single URLs that any agent (Cursor / Claude Code
  / Codex with WebFetch) can ingest for up-to-date jellycell context.
  Autodoc2-generated apidocs excluded from `llms.txt` to keep the index
  curated; they flow through to `llms-full.txt`.
- **`context7.json`** at repo root registers jellycell with the
  [Context7](https://context7.com) MCP docs service. Users who run the
  Context7 MCP (`@upstash/context7-mcp` or `https://mcp.context7.com/mcp`)
  get jellycell's docs queryable alongside every other indexed library
  without per-library MCP installs. **User-initiated step**: submit the
  repo at [context7.com/add-library](https://context7.com/add-library)
  to kick off indexing.

### Docs — alignment

- **`docs/getting-started.md`** — new "Bootstrap agent DX" step after
  `jellycell init`; "Agent onboarding" section rewritten around
  `--write`.
- **`docs/index.md`** — "Agent-friendly" card updated with the new
  one-command flow.
- **`docs/project-layout.md`** — new "Multi-project / monorepo
  pattern" section documenting the one-AGENTS.md-at-repo-root
  convention + how jellycell's tooling enforces it.
- **`docs/cli-reference.md`** — full `--write` / `--force` /
  `--agents-only` documentation + monorepo-safety note.
- **README.md** — quickstart gains the `jellycell prompt --write`
  line; "Agents drop in without onboarding" bullet updated.

### Contracts (§10)

- §10.1 `--json` schemas: `InitReport` gains `agents_md_hint: str | None`
  (additive, no bump). `PromptWriteReport` is new.
- §10.2 cache key: unchanged. `MINOR_VERSION` stays at 1.
- §10.3 agent guide content: **unchanged**. `jellycell prompt` stdout
  bytes are byte-identical; the snapshot at
  `tests/unit/test_prompt_snapshot/test_prompt_snapshot.yml` is not
  regenerated.

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

`site/` (HTML catalogue for browsers) and `manuscripts/` (prose for humans + GitHub) are separate output folders by design: neither is source; edit `notebooks/` and regenerate both.

- **`jellycell render`** produces self-contained HTML under `site/`. Templates use jinja2; code highlighting via Pygments; markdown via markdown-it-py + MyST plugins.
- **`jellycell view`** (needs `[server]` extra) serves a Starlette + SSE app with live-reload on file changes. Routes: `/`, `/nb/<stem>`, `/artifacts/<...>`, `/_assets/<...>`, `/api/state.json`, `/events`. Read-only.
- **Disk-write-free live viewer.** `jellycell view` renders every HTML page in memory; `jellycell render` is the only command that populates `site/`. `Renderer` carries a `write_pages: bool = True` kwarg — the CLI writes HTML to disk; the server passes `write_pages=False` and streams responses straight from memory.
- **Response cache on the live server.** Per-notebook and index caches are keyed on a view-key that combines the notebook's source bytes + its ordered cell cache keys — any edit or any run rotates the key, so cache correctness falls out of the keying. `JELLYCELL_VIEW_NOCACHE=1` disables the cache for template iteration.
- **Long-lived `RendererEnv`.** Jinja templates + Pygments CSS + assets dir are compiled once at server startup (`RendererEnv.for_server(project)`) and reused across requests; per-request `CacheStore` / `CacheIndex` handles stay short-lived for SQLite thread safety. `RendererEnv.for_static(project)` is the CLI factory.
- **Two asset trees.** Static `jellycell render` writes image blobs to `site/_assets/` (portable — upload the folder). `jellycell view` writes to `.jellycell/cache/assets/` (content-addressed, always git-ignored) and mounts it at `/_assets/`. Independent trees; content-hashed filenames dedupe within each tree, no sync logic.
- **Security warning on non-loopback `jellycell view`.** Binding `--host 0.0.0.0` (or any non-`127.0.0.1`/`localhost`/`::1` host) prints a banner about the exposure.

### Features — export

- **`jellycell export ipynb <nb>`** produces a runnable `.ipynb` with cached outputs reattached. `execution_count` matches nbformat convention (last `execute_result`, not first).
- **`jellycell export md <nb>`** produces MyST markdown for Sphinx / Jupyter Book integration.
- **`jellycell export tearsheet <nb>`** writes a curated markdown tearsheet to `manuscripts/tearsheets/<stem>.md` by default (override with `-o PATH`). The `tearsheets/` subfolder convention keeps auto-generated output separate from hand-authored writeups (paper drafts, memos, thesis chapters) that live at the root of `manuscripts/`. Pulls markdown cell prose, inlines image artifacts via relative paths, and flattens JSON summaries into two-column tables. Header block labels the file as a tearsheet with a link to the source notebook, to `site/<stem>.html` when it exists, and the last-run timestamp. Safe to commit — GitHub renders it inline. Example tearsheets ship under `examples/*/manuscripts/tearsheets/`.

### Features — agent surface

- **`jellycell prompt`** emits the canonical agent guide — a single markdown doc covering layout, format, tags, API, and CLI reference. Content is the §10.3 stability contract; pinned by a regression snapshot.
- Every CLI command supports `--json` with a versioned schema (§10.1). Shapes pinned by per-command regression snapshots.

### Docs + infra

- Docs on Read the Docs: getting-started, file-format, project-layout, cli-reference, agent-guide, plus the frozen v0 spec and dev guides.
- Examples: `minimal/`, `demo/`, `timeseries/`. CI runs every example notebook end-to-end.
- Claude Code infra: CLAUDE.md, slash commands (`/spec-check`, `/phase-status`), subagents, skills (`spec-invariant`, `phase-budget`, `piggyback-first`).
- Release pipeline on PyPI via trusted publisher (OIDC).

### Features — live viewer: manuscripts + journal + tearsheet nav

- **Manuscript previewer**: `/manuscripts/` landing page + dynamic
  `/manuscripts/<path>.md` route serves any markdown under
  `manuscripts/` through the project's template stack. Authored
  writeups, auto-generated tearsheets, and the journal all render
  in-browser with the same chrome as notebook pages.
- **Journal viewer**: `/journal` is a first-class route aliasing the
  configured journal file. Live-reloads on every `jellycell run`
  through the watchfiles → SSE pipeline so the trajectory appears
  in-browser as it's written.
- **Tearsheet ↔ notebook cross-links**: each notebook HTML page
  shows a `Tearsheet →` button when `manuscripts/tearsheets/<stem>.md`
  exists; tearsheet pages show a matching `Notebook →` link when the
  source notebook is present. One click to flip between source and
  curated summary.
- **Per-tearsheet prev/next navigation**: when browsing a tearsheet,
  the header carries `← previous / next →` links to the adjacent
  tearsheets in alphabetical order. Authored writeups don't get the
  prev/next pair since they're standalone documents.
- **Sidebar on manuscript pages**: three groups
  (Authored / Tearsheets / Log) with the active page highlighted.
- **Targeted SSE reloads**: `manuscripts/**/*.md` edits publish a
  `ReloadEvent` for the specific page (`/manuscripts/<path>` or
  `/journal`) rather than broadly reloading the index.
- **`/api/state.json`** carries a `manuscripts` payload
  (authored + tearsheets + journal catalog).

### Features — artifact metadata + journal + checkpoint

- **Artifact metadata via `jc.*` kwargs** — `jc.save`, `jc.figure`, and
  `jc.table` accept optional `caption="..."`, `notes="..."`, `tags=[...]`,
  captured on the `ArtifactRecord` inside the cell manifest. Tearsheets
  render caption as the figure / table heading, notes as an italic
  subcaption, tags as a searchable line below.
- **Analysis journal** — `manuscripts/journal.md` gets one append-only
  section per `jellycell run`: timestamp, notebook, cell counts,
  duration, new artifacts (with captions), large-artifact warnings,
  any errors, and the optional `-m "..."` message. Default-on (opt-out
  via `[journal] enabled = false`). Append-only from jellycell's side
  so hand-edited commentary survives future runs. `-m / --message` flag
  on `jellycell run` adds freeform commentary to the entry.
- **`jellycell checkpoint`** — reproducible `.tar.gz` snapshots with
  `create`, `list`, `restore` subcommands. Archives notebooks, data,
  artifacts, site, manuscripts, `jellycell.toml`, and
  `.jellycell/cache/`. Junk dirs (`__pycache__`, `.venv`, `.git`, etc.)
  are skipped. **Restore is safe by default**: lands in a new sibling
  directory (`<project>-restored-<name>/`) so the live project is
  never touched. `--into PATH` lets you pick a location; `--force` is
  required to merge into a non-empty target.

### Features — artifact layout + large-file handling

- **`[artifacts]` config section** in `jellycell.toml`:
  - **`layout`** (`"flat"` / `"by_notebook"` / `"by_cell"`, default
    `"flat"`): controls where path-less `jc.figure()` / `jc.table()`
    writes. `"by_cell"` makes every artifact path name its producer
    (`artifacts/<notebook>/<cell>/<name>.<ext>`) — agent-friendly for
    "what generated what" lookups. Explicit `jc.save(x, "...")` paths
    always win.
  - **`max_committed_size_mb`** (default `50`): post-run soft threshold.
    `jellycell run` flags any single artifact above the limit with a
    `.gitignore` / Git LFS reminder. Set to `0` to disable.
- **`large-data` example** under `examples/large-data/`
  demonstrates the full pattern: `[artifacts] layout = "by_notebook"`,
  low `max_committed_size_mb`, a tiny committed `headline.json` digest
  next to a git-ignored generated parquet, and a reproducible seed so
  reviewers regenerate locally.
- **`RunReport.large_artifacts` field** — a list of
  `LargeArtifactWarning` entries surfaced to both the JSON and rich
  outputs of `jellycell run`.

### Examples — READMEs + hand-authored manuscripts

Every example ships a top-level `README.md` with bootstrap commands
(both `uv` and `pip`), a layout diagram, and "what this example shows."
Every example's `manuscripts/` folder carries a hand-authored
`.md` alongside the auto-generated tearsheet(s):

- `minimal/manuscripts/notes.md` — first-run reflection.
- `demo/manuscripts/analysis.md` — analyst's read on the conversion numbers.
- `paper/manuscripts/paper.md` — paper draft, cross-linked to the tearsheet.
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

[Unreleased]: https://github.com/random-walks/jellycell/compare/v1.1.2...HEAD
[1.1.2]: https://github.com/random-walks/jellycell/releases/tag/v1.1.2
[1.1.1]: https://github.com/random-walks/jellycell/releases/tag/v1.1.1
[1.1.0]: https://github.com/random-walks/jellycell/releases/tag/v1.1.0
[1.0.0]: https://github.com/random-walks/jellycell/releases/tag/v1.0.0
