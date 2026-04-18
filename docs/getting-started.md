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

```bash
jellycell prompt > /tmp/agent-context.md
```

Pipe that into your agent's context and it knows the whole format, tag
vocabulary, `jc.*` API, and CLI.

## What next

- [File format](file-format.md) — complete PEP-723 + tag reference.
- [Project layout](project-layout.md) — everything in `jellycell.toml`.
- [CLI reference](cli-reference.md) — every command.
- [Agent guide](agent-guide.md) — the canonical `jellycell prompt` output.
