---
name: piggyback-first
description: Check the piggyback map in docs/reference/architecture.md before writing parsing, caching, rendering, file-watching, templating, or HTML-conversion code for jellycell. Also use when adding a new dependency to pyproject.toml. Prevents reimplementing what well-maintained libraries already do.
---

The entire point of jellycell is the **composition** of mature libraries, not reinventing them. Before writing code, ask: **is this job already done by one of our dependencies?**

## The piggyback map (reference/architecture)

| Task                              | We use                                                 | What we own                                        |
| --------------------------------- | ------------------------------------------------------ | -------------------------------------------------- |
| Parse `.py` / `.md` notebooks     | `jupytext`                                             | Tag vocabulary, PEP-723 extraction, dep graph      |
| In-memory notebook IR             | `nbformat.NotebookNode` for I/O                        | Our pydantic `Notebook`/`Cell` for logic           |
| Kernel subprocess                 | `jupyter-client` (`KernelManager`, `BlockingKernelClient`) | Per-cell orchestration, timeouts, streaming   |
| Output capture                    | Jupyter message protocol (via jupyter-client)          | Writing mime bundles to the cache                  |
| Cache blob store                  | `diskcache`                                            | Key derivation, manifest format, SQLite index      |
| Mime bundle → safe HTML           | `nbconvert` output helpers (NOT full HTMLExporter)     | The page shell, navigation, artifact links         |
| Markdown rendering                | `markdown-it-py` + MyST plugins                        | Tag-aware preprocessing                            |
| Templating                        | `jinja2`                                               | The templates themselves                           |
| File watching                     | `watchfiles`                                           | Debouncing, mapping file → notebook → clients      |
| Live-reload transport             | `sse-starlette`                                        | Event schema, client reconnect story               |
| ASGI server                       | `starlette` + `uvicorn`                                | Routes                                             |
| CLI framework                     | `typer`                                                | Command shape, `--json` contract                   |
| Config validation                 | `pydantic` + `tomllib` / `tomli-w`                     | Schemas                                            |
| ipynb round-trip                  | `nbformat` (write) + our cache (reattach outputs)      | Conversion logic                                   |

## Two anti-piggybacks (deliberately not used)

- **jupyter-cache** — caches whole notebooks; we need per-cell keying with explicit deps. Thin cache over `diskcache` is smaller than bending jupyter-cache.
- **full `nbconvert.HTMLExporter`** — has its own template system assuming notebook-as-document. We want project-wide catalogue. Use `nbconvert`'s output transformers, write the shell ourselves.

## Use this skill by asking

1. **What job am I about to do?** (e.g., "parse PEP-723 block", "watch a directory for changes")
2. **Is it in the piggyback map above?** Check column 1.
3. **If yes**: use the named lib. Our value-add is in column 3 (what we own), not column 2.
4. **If no**: proceed, but sanity-check — is there a widely-used lib you're not seeing? `WebSearch` for `"python <job> library"` if unsure.

## When adding a new dependency

Before running `uv add foo`:

1. Read pyproject.toml — is something similar already in our dep tree?
2. Check the piggyback map — are we supposed to use an existing dep for this?
3. If truly new: add with a version floor (`foo>=N.M`), add a comment explaining why, and update the piggyback map in `docs/reference/architecture.md` if it's a load-bearing dep.

## Reference

- `docs/reference/architecture.md` — living authoritative piggyback map + 8-layer dependency order.
- `CLAUDE.md` — the "Piggyback reminders" section for quick lookup.
- `docs/spec/v0.md` §1 — frozen genesis map (historical).
