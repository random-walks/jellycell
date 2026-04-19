# Changelog

All notable changes to jellycell follow the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format, and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versioning policy: **patch bumps are cheap**. See [docs/development/releasing.md](docs/development/releasing.md) for the full policy and the three §10 contracts that govern major bumps.

## [Unreleased]

## [1.3.5] — 2026-04-19

Two bundled patches: tearsheet artifact filtering via a declarative
``tearsheet`` tag (closes
[#15](https://github.com/random-walks/jellycell/issues/15)) and
CI-stability diagnostics for an intermittent Ubuntu-runner iopub
hang (see
[#21](https://github.com/random-walks/jellycell/issues/21)). No
runtime behavior change for healthy kernels.

### Export — ``tearsheet`` tag opt-in

Notebooks with many intermediate debug artifacts previously produced
noisy tearsheets; cleaning up required either deleting intermediate
files or hand-editing the generated markdown (both lost on
regeneration). Now you can mark the polished subset with a
``tearsheet`` tag at either granularity:

```python
# Cell-level — every artifact from this cell is included.
# %% tags=["jc.figure", "name=fig1", "tearsheet"]
jc.figure("artifacts/headline.png", caption="Main result")

# Or artifact-level — fine-grained (a cell can produce many artifacts,
# only some tearsheet-worthy):
jc.save(debug_dict, "artifacts/debug.json")                  # excluded
jc.save(headline, "artifacts/headline.json",
        tags=["tearsheet"])                                  # included
```

Filtering is **auto-enabled** when any artifact in the run carries
the tag (cell- or artifact-level). A notebook with no tagging
behaves exactly as before — every renderable artifact is inlined.

### Why tag-based over CLI flag

We considered a ``--include-artifacts`` glob flag for one-off
exports. Tag-based is declarative and persistent: the notebook
self-documents which artifacts are tearsheet-worthy, and every
subsequent ``jellycell export tearsheet`` produces the same output
without re-typing globs. A follow-up minor can layer a CLI override
on top if it turns out to be necessary.

### Fixed — kernel-timeout evalue now carries flake-triage diagnostics

``Kernel.execute`` records the iopub message mix, first-busy timing,
last-message timestamp, and kernel-liveness at timeout, and folds
them into the timeout's ``evalue``. When the flake surfaces again
the failure line tells us whether the kernel went ``busy`` at all,
how long it's been since any iopub traffic, and whether the
subprocess is still alive — which is what we need to decide between
"kernel truly hung" and "cell truly running long" without attaching
a debugger.

Additionally, ``Kernel.execute`` now sends SIGINT to the kernel on
timeout so the stuck cell bails out and the kernel is reusable for
follow-up work (regression-tested in
``test_interrupt_lets_kernel_reused_after_timeout``).

### Changed — `tests/examples/test_examples_run.py` retries once on Timeout

Until we have a root cause we don't want the flake to redden the
board. The test wraps ``Runner.run`` with a one-shot retry bounded
to ``Timeout`` errors (all other failure modes still fail on
attempt 1), and the retry uses ``force=True`` so cached ``jc.load``
cells re-execute in the fresh kernel — otherwise a hung-cell's
dependencies (imports, globals) would be missing on attempt 2. The
hung-attempt diagnostics are printed to stderr so CI logs carry
evidence even when attempt 2 saves the run.

### Contracts (§10)

- All unchanged. No cache-key / JSON schema / agent-guide touches.
  The tearsheet tag is opt-in and additive; untagged notebooks are
  byte-for-byte identical to the 1.3.1 tearsheet output. The kernel
  timeout diagnostics only surface on error paths — healthy kernels
  see no behavior change.

## [1.3.4] — 2026-04-19

`jc.table` first-run ergonomics patch — pyarrow is now shipped by
default, and mixed-dtype object columns (common in regression
output) round-trip instead of crashing pyarrow's parquet writer.
Closes [#13](https://github.com/random-walks/jellycell/issues/13)
and [#14](https://github.com/random-walks/jellycell/issues/14).

### Deps — `pyarrow` is a default dependency

Before 1.3.4, calling `jc.table(df)` on a clean install raised
`ImportError: Unable to find a usable engine; tried using: 'pyarrow',
'fastparquet'` because pandas needs a parquet engine and pyarrow
isn't a pandas-core dep. Every user hit this on the first `jc.table`
cell.

`pyarrow>=15` moved from the `[examples]` optional extra into
`[project].dependencies`. Rationale:

- pandas 3.x is moving toward pyarrow-backed dtypes by default, so
  pyarrow is becoming non-optional for most pandas users anyway.
- The wheel is ~30 MB — small enough that the default-install cost
  is outweighed by a working first-run.
- `jc.table` is the canonical tabular primitive; a user running
  their first notebook shouldn't have to diagnose a pandas error to
  find out they need a separate package.

Also, as a belt-and-suspenders for environments where pyarrow is
somehow missing at runtime (forcibly uninstalled, import failure),
`jc.table` now re-raises any `ImportError` from `to_parquet` with a
clean message pointing at `pip install pyarrow`.

### API — mixed-dtype columns auto-cast to string

`jc.table` now detects object columns whose inferred dtype is
``mixed*`` (per `pandas.api.types.infer_dtype`) and casts them to
string before writing. Pure-string and pure-numeric columns are
untouched.

Before:

```python
df = pd.DataFrame({"var": ["x", "y"], "p": ["<.001", 0.84]})
jc.table(df, name="ols")
# → ArrowInvalid: Could not convert '<.001' with type str: tried to
#   convert to double (deep in pyarrow's parquet writer).
```

After: the `p` column is cast to string before write, round-trips as
string on `pd.read_parquet`. The information loss is minimal for the
common case (p-values, categorical labels that may have been typed
as numbers); callers who need a specific dtype should pre-cast
explicitly.

### Contracts (§10)

- All unchanged. No cache-key, JSON schema, or agent-guide content
  touched. The auto-cast is additive behavior that surfaces on an
  input type that previously crashed, so it doesn't affect
  round-trips for any DataFrame that worked in 1.3.1. Adding a
  default dependency is a standard patch-level change.

## [1.3.3] — 2026-04-19

CLI ergonomics patch — `jellycell run` and `jellycell export *` now
honor the global `--project ROOT` flag (previously wired up for
`render`, `cache`, `checkpoint`, `lint`, `new`, `view` but silently
ignored by run / export). Closes
[#12](https://github.com/random-walks/jellycell/issues/12).

### CLI — `--project` resolves notebook paths project-relative

Before 1.3.3, `jellycell run` and `jellycell export *` walked up from
the notebook path to find `jellycell.toml` but ignored any explicit
`--project` flag — so automation targeting a specific project root
had to prefix every notebook path with the project's subdir:

```bash
# Old: verbose, requires knowing the exact prefix layout.
for showcase in showcase-*; do
  for nb in "$showcase"/notebooks/*.py; do
    uv --directory packages/python-showcase run jellycell export tearsheet \
       "$showcase/$(basename "$nb")"
  done
done
```

Now `--project` works symmetrically for both commands:

```bash
# New: notebook path resolves under --project automatically.
for showcase in packages/python-showcase/showcase-*; do
  for nb in "$showcase"/notebooks/*.py; do
    jellycell --project "$showcase" export tearsheet \
       "notebooks/$(basename "$nb")"
  done
done
```

### Resolution order

The new `resolve_notebook_and_project()` helper in `jellycell.cli.app`:

- **`--project ROOT` set**: load project from `ROOT/jellycell.toml`
  directly (no walk-up). Resolve notebook as `ROOT/<notebook>` first,
  falling back to `cwd/<notebook>` if the project-relative path
  doesn't exist. Absolute notebook paths are honored verbatim.
- **`--project` not set**: unchanged — resolve notebook against cwd,
  then walk up to find `jellycell.toml`.

### New API

`Project.from_root(root)` — loads a project directly from a known
root without walking up. Raises `ProjectNotFoundError` if
`root/jellycell.toml` is missing.

### Contracts (§10)

- All unchanged. No cache key / JSON schema / agent guide touches.
  `--project` semantics are already documented globally; wiring the
  last two commands up is bringing them in line with the others.

## [1.3.2] — 2026-04-19

Two independent patches landing in the same release slot — both
came out of blaise-website dogfood. Thanks to the agent for the
tight repros.

### Fixed — `jc.setup` cells are no longer cached

Closes [#10](https://github.com/random-walks/jellycell/issues/10).
Before this release, the runner treated setup cells like any other
code cell: it computed a cache key, and on a cache hit it skipped
execution entirely. But every `jellycell run` spawns a **fresh
kernel** — so a cached setup cell's side effects (imports, module
aliases, global constants) never landed in the kernel namespace.
Downstream cache-miss cells that referenced those imports then
failed at runtime with `NameError`.

Minimal reproducer (fails on 1.3.1):

```python
# notebook.py
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

# %% tags=["jc.setup"]
import jellycell.api as jc
from IPython.display import Image

# %% tags=["jc.figure", "name=fig1"]
Image("artifacts/figures/foo.png")
```

Run once (both cells `ok`). Edit the figure cell. Run again: cell 1
reports `cached` (wrong — docs said uncached), cell 2 fails with
`NameError: name 'Image' is not defined`.

1.3.2 takes the preferred of the two fixes noted on the issue:
**skip the cache for `jc.setup` cells unconditionally** (match the
docs). Setup cells now always execute, carry no cache key in the
run report (`cache_key=null`), and leave no manifest / index entry.

### Added — `jc.figure(path)` accepts path-only invocation

Closes [#11](https://github.com/random-walks/jellycell/issues/11).
Verbatim-mirror analyses with pre-rendered images on disk no longer
need an `IPython.display.Image` workaround inside a `jc.figure`-tagged
cell. `jc.figure` now has two modes:

- **Render** (unchanged) — `fig=` given, or omitted with `plt.gcf()`
  available: save the figure to `path`, honoring `[artifacts] layout`
  when `path` is `None`.
- **Path-only** (new) — `fig` omitted *and* `path` points to an existing
  image file: skip the matplotlib re-encode. The file is registered
  as an artifact (with caption / notes / tags flowing to the manifest)
  and inlined via IPython `display(Image(...))` so the cell renders
  in HTML/ipynb output.

Reduces this boilerplate…

```python
# %% tags=["jc.figure", "name=fig1"]
from IPython.display import Image
Image("artifacts/figures/figure-1.png")
# — inlines fine but loses caption/notes/tags for the manifest.
```

…to:

```python
# %% tags=["jc.figure", "name=fig1"]
jc.figure(
    "artifacts/figures/figure-1.png",
    caption="System-wide ADA coverage",
)
```

Fully backwards-compatible: existing call sites with explicit `fig=`
keep their current behavior. Falling through to the render path
when the file doesn't exist yet means the old "create on first run"
pattern also still works.

### Contracts (§10)

- **§10.2 cache key algorithm**: untouched. The setup-cells fix
  changed *when the runner consults the cache*, not how keys are
  computed; no `MINOR_VERSION` bump, existing cache entries for
  non-setup cells remain valid.
- **§10.1 `--json` schemas**: `RunReport` shape unchanged.
  `CellResult.cache_key` was already `str | None`; setup cells now
  reliably fall into the `None` branch.
- **§10.3 agent guide**: already accurate. The setup-cells behavior
  matches what the guide described all along; the new `jc.figure`
  path-only mode is additive behavior callers opt into by dropping
  `fig=`.

## [1.3.1] — 2026-04-19

Docs patch — fixes a self-contradicting pnpm wrapper recipe
surfaced by a real polyglot dogfood (thanks to the blaise-website
agent for the clean repro).

### Docs — pnpm wrapper recipes use `uv --directory`

The `docs/project-layout.md` *pnpm wrapper recipes* block in 1.3.0
shipped every script using `uv --project packages/python-showcase`,
but the usage examples that follow used `uv --directory`. For any
showcase nested under `packages/python-showcase/` (the whole point
of the section) `uv --project` keeps cwd at the repo root, so
`pnpm showcase:run showcase-marketing/notebooks/tour.py` resolves
against the repo root — **fails with "No jellycell.toml found"**.

`uv --directory <path>` cd's into `<path>` before running, so
relative showcase paths resolve under the Python package root —
which is what every `showcase:*` script wants. Every wrapper now
uses `uv --directory`. A short "why" paragraph explains when
`uv --project` is still the right call (the one-shot
`jellycell prompt --write` under Pattern B, where you want cwd
pinned at the monorepo root so AGENTS.md lands there).

Reproduce the old bug:

```bash
cd /tmp/anyrepo && git init -q
uv init --package packages/python-showcase
mkdir -p packages/python-showcase/foo/notebooks
uv --project packages/python-showcase run jellycell run foo/notebooks/x.py
# → "No jellycell.toml found walking up from /tmp/anyrepo/foo/notebooks/x.py"
```

No code changes. No contracts touched.

### Contracts (§10)

- All unchanged. Docs-only patch.

## [1.3.0] — 2026-04-19

Polyglot UX fixes from real-world dogfood: a new `--nested` flag that
removes a `--force` misnomer, plus docs that actually describe the
two legitimate AGENTS.md placements instead of framing one as a trap.

### Features — `jellycell prompt --write --nested`

- **New `--nested` flag**. Acknowledges an outer `AGENTS.md` detected
  in an ancestor and writes an intentional inner override at the
  target without needing `--force`. Still refuses to clobber an
  existing target file (use `--force` for that). Semantics:

  | Target state                                      | Flag       |
  | ------------------------------------------------- | ---------- |
  | No outer, no existing target file                 | (none)     |
  | Outer AGENTS.md exists, no existing inner file    | `--nested` |
  | Existing target file (any scope)                  | `--force`  |
  | Outer AGENTS.md + existing inner target           | `--nested --force` |

  Before 1.3.0, adopting the polyglot "nested" layout required
  `--force`, which semantically implied "clobber everything" and
  lumped two distinct intents (acknowledge outer / overwrite target)
  into one flag. `--nested` separates them.

- **`PromptWriteReport.nested: bool`** field added to the `--json`
  output (§10.1 additive — no `schema_version` bump). `true` when
  `--nested` was passed AND an outer `AGENTS.md` was detected;
  `false` otherwise (including on `--force`-only writes that
  happened to suppress the same check).

- **Error message on outer-detection** now surfaces both escape
  hatches: "Re-run with `--nested` to intentionally add an inner
  override for this subtree, or `--force` to bypass all checks."

### Docs — polyglot patterns

- **`docs/project-layout.md` polyglot subsection** rewritten around
  two defensible AGENTS.md placements:
  - *Pattern A (recommended for polyglot)* — `AGENTS.md` at the
    Python subtree (`packages/python-showcase/AGENTS.md`) alongside
    an outer repo-wide `AGENTS.md` at the git root. Agents compose
    both per the AGENTS.md spec.
  - *Pattern B* — single `AGENTS.md` at the git root.

  Use `uv --directory` (cd's in) + `--nested` for Pattern A; use
  `uv --project` (stays in cwd) for Pattern B. Previous 1.2.0
  wording framed `uv --directory` as a trap, which was only correct
  for Pattern B.
- **pnpm wrapper recipes** added for the `--project` Typer-global
  footgun. Jellycell's `--project <path>` must precede the
  subcommand, which conflicts with pnpm's natural "positional arg
  at the end" script shape. A tiny `bash -c '… --project "$1"
  <subcmd> "${@:2}"' --` wrapper bridges it; the new subsection
  shows five ready-to-paste scripts (`showcase:run`, `showcase:init`,
  `showcase:render`, `showcase:view`, `showcase:lint`).
- **"If you already have an AGENTS.md" note** documents the current
  clobber-or-hand-merge reality plus the `AGENTS.jellycell.md`
  sibling-file workaround. Previews a future `jellycell prompt
  --append` flag using Next.js-style `<!-- BEGIN:jellycell -->` /
  `<!-- END:jellycell -->` marker blocks (that's the emerging
  community convention; agents.md spec is silent). Shipping the
  append flag itself is a future minor — this release just
  documents intent.
- **`docs/cli-reference.md`** — `--nested` documented with the
  full flag table.
- **`docs/agent-guide.md`** — "Single-project vs monorepo"
  section updated to mention `--nested` (§10.3 additive; snapshot
  regenerated from 11915 → 12140 bytes; canonical headers
  preserved).
- **`examples/monorepo/README.md`** polyglot section updated to
  show `--nested` in the Pattern A command.

### Contracts (§10)

- §10.1 `--json` schemas: **additive** — `PromptWriteReport` gains
  `nested: bool` field. No `schema_version` bump. Snapshot
  regenerated.
- §10.2 cache key: unchanged. `MINOR_VERSION` stays at 1.
- §10.3 agent guide content: **additive** — one paragraph added to
  the existing "Single-project vs monorepo" section. Snapshot
  regenerated.

## [1.2.0] — 2026-04-19

Monorepo patterns — one Python env, multiple jellycell projects — now
have a runnable reference fixture, explicit documentation, and
agent-guide coverage. §10.3 additive content → minor bump.

### Docs — single-project vs monorepo

- **`docs/agent-guide.md`** gains a "Single-project vs monorepo"
  section covering the two patterns, the monorepo-aware behavior of
  `jellycell init` and `jellycell prompt --write`, and the correct
  command forms (`jellycell run <subdir>/notebooks/foo.py` or
  `jellycell --project <subdir> <command>`). §10.3 additive —
  snapshot regenerated; no existing guidance modified.
- **`docs/project-layout.md` Multi-project / monorepo pattern**
  expanded with explicit "jellycell monorepo" framing (one
  `pyproject.toml` / `uv.lock` / `.venv` at the root hosting all
  projects), a "Running commands in a monorepo" subsection showing
  both forms, a `--project` vs path-anchored discovery footgun note,
  and a polyglot subsection for Python packages nested inside a
  pnpm/turbo/Node repo.
- **`docs/getting-started.md`** now asks "Single project or monorepo?"
  right after `jellycell init`, pointing at the runnable example and
  the full project-layout section.

### Examples

- **New [`examples/monorepo/`](examples/monorepo/)** fixture — a
  minimal runnable layout with one `pyproject.toml` at the root, two
  sibling jellycell projects (`showcase-marketing` + `showcase-churn`),
  and a curated `AGENTS.md` placeholder that agents regenerate with
  `uv run jellycell prompt --write --force`. Demonstrates cache
  isolation: running one showcase doesn't invalidate the other's
  cache; each gets its own `.jellycell/cache/`, `artifacts/`, and
  `site/`.

### Contracts (§10)

- §10.1 `--json` schemas: unchanged.
- §10.2 cache key: unchanged. `MINOR_VERSION` stays at 1.
- §10.3 agent guide content: **additive section** ("Single-project vs
  monorepo"). Snapshot `tests/unit/test_prompt_snapshot/test_prompt_snapshot.yml`
  regenerated — length 11066 → 11915 bytes, all four canonical
  headers still present, existing section content byte-identical.

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

[Unreleased]: https://github.com/random-walks/jellycell/compare/v1.3.1...HEAD
[1.3.1]: https://github.com/random-walks/jellycell/releases/tag/v1.3.1
[1.3.0]: https://github.com/random-walks/jellycell/releases/tag/v1.3.0
[1.2.0]: https://github.com/random-walks/jellycell/releases/tag/v1.2.0
[1.1.2]: https://github.com/random-walks/jellycell/releases/tag/v1.1.2
[1.1.1]: https://github.com/random-walks/jellycell/releases/tag/v1.1.1
[1.1.0]: https://github.com/random-walks/jellycell/releases/tag/v1.1.0
[1.0.0]: https://github.com/random-walks/jellycell/releases/tag/v1.0.0
