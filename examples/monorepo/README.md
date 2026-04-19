# Multi-project monorepo

A minimal reference layout showing **one uv-managed Python environment
hosting several jellycell projects** in the same repo, with a single
shared agent guide at the root. Use this pattern when one codebase
holds multiple independent analyses that deserve separate caches,
artifact trees, and rendered sites — a personal site's OSS showcases,
a consulting repo with per-client workbooks, a paper with multiple
experiments, etc.

```
examples/monorepo/                  # the repo root
├── pyproject.toml                  # one uv environment for the whole repo
├── .python-version                 # pinned interpreter
├── .gitignore                      # covers .venv, per-showcase .jellycell/, site/
├── AGENTS.md                       # one agent guide covering every showcase
├── CLAUDE.md                       # stub pointing at AGENTS.md
├── showcase-marketing/             # one jellycell project
│   ├── jellycell.toml
│   └── notebooks/
│       └── tour.py
└── showcase-churn/                 # another jellycell project
    ├── jellycell.toml
    └── notebooks/
        └── tour.py
```

## Why this layout

- **One `pyproject.toml` + `.venv` at the root.** Every showcase runs
  against the same environment, so you only `uv sync` once per machine
  instead of per project. Jellycell (and any shared deps) lives at the
  top, each showcase's PEP-723 block can still add project-specific
  deps.
- **One `AGENTS.md` at the root.** `jellycell init` and
  `jellycell prompt --write` walk ancestors for an existing `AGENTS.md`,
  stopping at the repo's `.git/` directory, so a single file at the
  root covers every showcase. `jellycell prompt --write
  showcase-marketing/` refuses to scatter a duplicate (pass `--force`
  only if you want an inner override).
- **One `jellycell.toml` per project.** Jellycell discovers the
  nearest `jellycell.toml` walking up from cwd. Each showcase has its
  own `notebooks/`, `artifacts/`, `site/`, `manuscripts/`, and
  `.jellycell/cache/` — zero cross-leak.
- **The monorepo root has no `jellycell.toml`.** It's not a jellycell
  project; it's the container. Commands from the root need
  `--project <showcase>` or a `cd <showcase>` first.

## Bootstrap

```bash
# 1. Clone (or `uv init` a new repo + copy this structure).
# 2. Install the shared Python environment once:
uv sync

# 3. Run an existing showcase (project discovery walks up from the
#    notebook path, so no --project flag needed):
uv run jellycell run showcase-marketing/notebooks/tour.py

# 4. Scaffold a new showcase. The command detects the outer AGENTS.md
#    automatically and prints "✓ agent guide detected at ../AGENTS.md"
#    instead of the usual "tip: add one" banner.
uv run jellycell init showcase-returns

# 5. Regenerate AGENTS.md + CLAUDE.md (e.g. after a jellycell upgrade).
uv run jellycell prompt --write --force
```

## Running a showcase

Two equivalent forms. Pick whichever matches your muscle memory:

```bash
# A) Full path from the monorepo root — jellycell discovers the
#    project by walking up from the notebook path. Simplest for
#    commands that take a notebook argument.
uv run jellycell run showcase-marketing/notebooks/tour.py

# B) cd into the showcase first. `jellycell.toml` discovery from cwd
#    does the rest.
cd showcase-marketing
uv run jellycell run notebooks/tour.py
uv run jellycell render
uv run jellycell view
```

For commands that don't take a notebook argument (`render` /
`view` / `lint` / `export`), use `--project` with no notebook:

```bash
uv run jellycell --project showcase-marketing render
uv run jellycell --project showcase-marketing view            # live viewer on :5179
uv run jellycell --project showcase-churn    lint --fix
```

Either form uses the same `.venv` at the monorepo root — no per-
showcase environment setup.

> `jellycell --project X run notebooks/tour.py` does **not** rewrite
> `notebooks/tour.py` to live under `X/` — that path is resolved
> against your current working directory. Use form A (full path) or B
> (`cd`) when running a notebook.

## What gets committed vs git-ignored

Commit:

- `notebooks/*.py` per showcase (source of truth).
- `jellycell.toml` per showcase; `pyproject.toml` + `uv.lock` +
  `.python-version` at the root.
- `AGENTS.md`, `CLAUDE.md`, `README.md`.
- Each showcase's `data/` (small files), `artifacts/` (outputs worth
  reviewing), and `manuscripts/` (hand-authored writeups +
  auto-generated tearsheets).

Git-ignore (this root `.gitignore` covers every showcase):

- `.venv/` at the root.
- Each showcase's `.jellycell/cache/` (content-addressed cache) and
  `site/` (regenerate with `jellycell render`).

## Polyglot monorepos

Nothing about jellycell's walk-up is Python-specific. If you drop this
structure deeper — `packages/python-showcase/showcase-marketing/` —
inside a pnpm/turbo/Next.js repo, jellycell still works identically,
provided `AGENTS.md` sits at the outer git root. Shell out through
`uv --directory packages/python-showcase run jellycell --project
<showcase> …` from your pnpm scripts.

## See also

- [`docs/project-layout.md#multi-project--monorepo-pattern`](https://jellycell.readthedocs.io/en/latest/project-layout.html#multi-project-monorepo-pattern) — the monorepo convention.
- [`docs/cli-reference.md#jellycell-prompt`](https://jellycell.readthedocs.io/en/latest/cli-reference.html#jellycell-prompt) — `jellycell prompt --write` behavior including outer-AGENTS.md detection.
- Other examples — [`minimal/`](../minimal), [`demo/`](../demo), [`paper/`](../paper), [`timeseries/`](../timeseries), [`ml-experiment/`](../ml-experiment), [`large-data/`](../large-data) — for single-project patterns.
