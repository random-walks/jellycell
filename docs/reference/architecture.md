# Architecture

How jellycell's pieces fit together, and what we deliberately don't
reinvent. Authoritative and kept up-to-date — if you add or remove a
load-bearing dep, or shift a subpackage's responsibilities, edit this
page in the same PR.

## Piggyback map

The point of jellycell is the **composition**. Before writing new code,
ask: is this already done by something we depend on?

| Task                              | We use                                                     | What we own                                        |
| --------------------------------- | ---------------------------------------------------------- | -------------------------------------------------- |
| Parse `.py` / `.md` notebooks     | `jupytext`                                                 | Tag vocabulary, PEP-723 extraction, dep graph      |
| In-memory notebook IR             | `nbformat.NotebookNode` for I/O                            | Our pydantic `Notebook` / `Cell` models for logic  |
| Kernel subprocess                 | `jupyter-client` (`KernelManager`, `BlockingKernelClient`) | Per-cell orchestration, timeouts, streaming        |
| Output capture                    | Jupyter message protocol (via `jupyter-client`)            | Writing mime bundles to the cache                  |
| Cache blob store                  | `diskcache`                                                | Key derivation, manifest format, SQLite index      |
| Mime bundle → safe HTML           | `nbconvert` output helpers (NOT full HTMLExporter)         | The page shell, navigation, artifact links         |
| Markdown rendering                | `markdown-it-py` + MyST plugins                            | Tag-aware preprocessing                            |
| Templating                        | `jinja2`                                                   | The templates themselves                           |
| File watching                     | `watchfiles`                                               | Debouncing, mapping file → notebook → clients      |
| Live-reload transport             | `sse-starlette`                                            | Event schema, client reconnect story               |
| ASGI server                       | `starlette` + `uvicorn`                                    | Routes                                             |
| CLI framework                     | `typer`                                                    | Command shape, `--json` contract                   |
| Config validation                 | `pydantic` + `tomllib` / `tomli-w`                         | Schemas                                            |
| `.ipynb` round-trip               | `nbformat` (write) + our cache (reattach outputs)          | Conversion logic                                   |

## Two deliberate anti-piggybacks

- **`jupyter-cache`** — caches whole notebooks; we need per-cell keying
  with explicit deps. A thin cache over `diskcache` is smaller than
  bending `jupyter-cache` to our model.
- **Full `nbconvert.HTMLExporter`** — has its own template system that
  assumes notebook-as-document. We want a project-wide catalogue. Use
  `nbconvert`'s output transformers (the bits that turn a mime bundle
  into safe HTML, handle base64 images, etc.); write the page shell
  ourselves.

If you're evaluating a new dep, update this table in the same PR.

## 8-layer dependency order

Upper layers depend only on lower ones. Break this and refactors cost
exponentially more.

```
CLI → Server → Render → Run → API → Cache → Format → Paths+Config
```

Concretely:

| Layer            | Subpackages                                                  | Imports only from                     |
| ---------------- | ------------------------------------------------------------ | ------------------------------------- |
| Paths + Config   | `jellycell.config`, `jellycell.paths`                        | stdlib + pydantic                     |
| Format           | `jellycell.format.*`                                         | Paths+Config + stdlib + jupytext      |
| Cache            | `jellycell.cache.*`                                          | Format and below                      |
| API              | `jellycell.api`, `jellycell.run.context`                     | Cache and below                       |
| Run              | `jellycell.run.*`                                            | API and below + jupyter-client        |
| Render           | `jellycell.render.*`                                         | Run and below + jinja2/nbconvert      |
| Server           | `jellycell.server.*`                                         | Render and below + starlette/watchfiles |
| CLI              | `jellycell.cli.*`                                            | Everything (entry point)              |
| Export           | `jellycell.export.*`                                         | Cache + Format; no kernel             |

### Invariants

- `cache/` **must not** import from `run/`, `render/`, `server/`. Cache
  is the lowest load-bearing layer; upper layers consume it.
- `export/` sits parallel to `render/` — both derive outputs from cached
  manifests without running a kernel.
- `run/context.py` lives on the Run/API boundary: API cells read it to
  know their cache key; the Runner writes it before executing a cell.

## Subpackage responsibilities

Minimum to carry in your head when navigating the tree:

- **`config.py`** — the pydantic schema for `jellycell.toml`. Changes
  here affect every layer, so new config sections need default values
  that preserve existing behavior.
- **`paths.py`** — the `Project` value object. The *only* place raw
  filesystem paths are resolved; every other layer takes a `Project`.
- **`format/`** — jupytext-backed notebook I/O plus our tag parser,
  PEP-723 strip-and-reinsert, and static AST analysis
  (`extract_static_deps`, `extract_loaded_paths`).
- **`cache/`** — `hashing.py` (cache key algorithm, §10.2), `store.py`
  (diskcache wrapper), `index.py` (SQLite catalogue accelerator +
  artifact lineage), `manifest.py` (pydantic schema for per-cell manifests).
- **`api.py`** — the `jc.*` surface. Every helper works both inside a
  run (reads `RunContext`) and as plain-script fallback (no context).
- **`run/`** — `kernel.py` (jupyter-client orchestration),
  `runner.py` (per-cell loop + cache decisions + manifest building),
  `pool.py` (kernel reuse for batch runs), `env_hash.py` (lockfile-aware).
- **`render/`** — jinja2 templates + nbconvert output helpers + asset
  deduplication. ``RendererEnv`` holds the shareable (and expensive)
  state — compiled Jinja env, Pygments CSS, assets dir — with two
  factory methods: ``for_static(project)`` (assets under
  ``site/_assets/``) and ``for_server(project)`` (assets under
  ``.jellycell/cache/assets/``). ``Renderer`` takes an optional ``env``
  + ``write_pages`` flag: the CLI path writes ``site/*.html`` to disk
  (default), the server path returns HTML strings and never touches
  ``site/``.
- **`server/`** — starlette app + SSE broker + watchfiles binding.
  Holds one long-lived ``RendererEnv`` per process and an in-memory
  response cache keyed on ``CacheIndex.notebook_view_key`` (source
  bytes + ordered cell cache keys). ``JELLYCELL_VIEW_NOCACHE=1``
  disables the cache for template development.
- **`cli/`** — typer commands. Every command emits `--json` with a
  versioned schema (§10.1).
- **`export/`** — derived-output generators: ipynb, MyST markdown,
  tearsheets.

## How the live viewer differs from `jellycell render`

Both paths share the same Jinja templates + output helpers, but diverge
deliberately in two ways:

| Concern               | `jellycell render` (CLI)       | `jellycell view` (server)              |
| --------------------- | ------------------------------ | -------------------------------------- |
| HTML pages            | `site/<stem>.html` on disk     | streamed HTML string, no disk write    |
| Image assets          | `site/_assets/<hash>.png`      | `.jellycell/cache/assets/<hash>.png`   |
| Response caching      | n/a (one-shot)                 | in-memory, keyed by notebook view-key  |
| Jinja / Pygments      | built per-invocation           | built once at app startup, reused      |
| Cache + SQLite        | opened per render              | same (per-request, thread-local)       |

**Why two assets dirs**: `site/_assets/` is part of the portable static
site you'd upload to a server or GitHub Pages. `.jellycell/cache/assets/`
is content-addressed blob storage parallel to the rest of the cache;
it's always gitignored, doesn't bloat the committed repo, and the live
server mounts it directly at `/_assets/`. If you use both modes in the
same project, you get assets in both places — small files, content-
hashed, no sync logic needed.

**Why response caching**: re-rendering an unchanged notebook on every
page reload is pure waste. The view-key changes on any edit (source
bytes) or any run (new cell cache keys), so the cache is always
correct without explicit busting.

## When to update this page

- **Always**: adding or removing a load-bearing dependency in
  `pyproject.toml`, moving responsibilities between subpackages,
  changing which layers a subpackage imports from.
- **Usually not**: adding a helper function to an existing subpackage,
  internal refactors that preserve the layering.

## See also

- [Contracts](contracts.md) — the three §10 invariants that bump major versions.
- [Project layout](../project-layout.md) — `jellycell.toml` schema.
- [v0 spec](../spec/v0.md) — historical genesis; this page is the
  living version of what was §1–§2 of the original spec.
