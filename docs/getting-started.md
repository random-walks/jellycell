# Getting started

Set up your first jellycell project, run a notebook end-to-end, view the
catalogue, and dogfood the dev loop.

## Install

```bash
pip install 'jellycell[server]'     # CLI + live viewer
# or
pip install jellycell                # CLI only (no `jellycell view`)
```

Requires Python ≥ 3.11. If you use [uv](https://docs.astral.sh/uv/):

```bash
uv tool install 'jellycell[server]'
```

## Create a project

```bash
jellycell init my-analysis
cd my-analysis
```

Scaffolds:

```
my-analysis/
├── jellycell.toml
├── notebooks/
├── data/
├── artifacts/
├── site/
└── manuscripts/
```

`jellycell init` also prints an AGENTS.md hint — either "✓ agent guide
detected at ../AGENTS.md" if one already covers this subtree, or a tip
showing how to add one. See the [next step](#bootstrap-agent-dx) to act
on the tip.

## Bootstrap agent DX

If you want Cursor / Codex / GitHub Copilot / Claude Code / Aider to
pick up jellycell's agent guide automatically, drop `AGENTS.md` +
`CLAUDE.md` at your **repo root** (not the project root — one covers
every jellycell project underneath):

```bash
cd my-repo     # the git root, which may contain multiple jellycell projects
jellycell prompt --write
```

Writes `AGENTS.md` (full guide, rendered as plain markdown — `:::` MyST
directives stripped) and `CLAUDE.md` (a 3-line stub pointing at
`AGENTS.md`, since Claude Code reads `CLAUDE.md` by convention).

If you later run `jellycell prompt --write` from inside a subdirectory
that already has an outer `AGENTS.md`, jellycell refuses and explains —
pass `--force` if you genuinely want an inner override. See
[project-layout.md](project-layout.md#multi-project--monorepo-pattern)
for the monorepo pattern.

## Write a notebook

Create `notebooks/hello.py` (or run `jellycell new hello`):

```python
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

# %% [markdown]
# # Hello jellycell

# %% tags=["jc.load", "name=raw"]
raw = {"a": 1, "b": 2, "c": 3}

# %% tags=["jc.step", "name=total", "deps=raw"]
import jellycell.api as jc

total = sum(raw.values())
jc.save({"raw": raw, "total": total}, "artifacts/summary.json")
print(f"total = {total}")
```

## Run it

```bash
jellycell run notebooks/hello.py
```

The first run executes every cell. On the second run, cells are cached:

```bash
jellycell run notebooks/hello.py      # all cached, finishes in ms
```

Change the source of any cell → only that cell (and its dependents) re-execute.

## Lint

```bash
jellycell lint
jellycell lint --fix       # auto-apply fixable violations
```

## See the result

Render static HTML:

```bash
jellycell render            # writes site/index.html + one page per notebook
```

Or serve live (watches for changes, SSE-reloads the page):

```bash
jellycell view
```

Opens `http://127.0.0.1:5179/`.

## Export

```bash
jellycell export ipynb notebooks/hello.py   # writes site/hello.ipynb
jellycell export md notebooks/hello.py      # MyST markdown for Sphinx/Jupyter Book
```

## Agent onboarding

The canonical agent guide lives at `jellycell prompt` — the single
source of truth for notebook format, tag vocabulary, `jc.*` API, and
every CLI command. Two flows:

```bash
jellycell prompt                    # print to stdout (pipe into any agent's context)
jellycell prompt --write            # drop AGENTS.md + CLAUDE.md at the repo root
```

The second is the one-command DX — AGENTS.md-native tools (Cursor,
Codex, GitHub Copilot, Aider, Zed, Warp, Windsurf) pick it up
automatically; Claude Code reads the `CLAUDE.md` stub that points to
the same file. See [Bootstrap agent DX](#bootstrap-agent-dx) above for
the monorepo-aware behavior.

## What next

- [File format](file-format.md) — complete PEP-723 + tag reference.
- [Project layout](project-layout.md) — everything in `jellycell.toml`.
- [CLI reference](cli-reference.md) — every command.
- [Agent guide](agent-guide.md) — the canonical `jellycell prompt` output.
