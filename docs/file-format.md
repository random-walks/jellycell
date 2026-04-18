# File format

A jellycell notebook is a Python file in **jupytext percent format** with an
optional **PEP-723 script block** at the top.

## Anatomy

```python
# /// script                                         ← PEP-723 block (optional)
# requires-python = ">=3.11"
# dependencies = ["pandas"]
#
# [tool.jellycell]                                   ← optional file-scope overrides
# timeout_seconds = 300
# ///

# %% [markdown]                                      ← markdown cell
# # Title

# %% tags=["jc.load", "name=raw"]                    ← tagged code cell
import pandas as pd
raw = pd.read_csv("data/input.csv")

# %% tags=["jc.step", "name=summary", "deps=raw"]
summary = raw.describe()
```

## PEP-723 block

Per [PEP 723](https://peps.python.org/pep-0723/): a `# /// script` block
containing TOML metadata.

Rules:

- **Must be at the top of the file.** Any content before the block (other than
  whitespace) is rejected by the lint rule `pep723-position`. `jellycell lint
  --fix` re-flows the file.
- **Optional.** A file without a block is valid and inherits project-level
  config from `jellycell.toml`.
- **`[tool.jellycell]` overrides `jellycell.toml` at file scope.** Other
  `[tool.X]` tables are preserved unchanged.
- The raw block text is round-tripped verbatim. `jellycell run`, `jellycell
  render`, and `uv run --script <notebook>` all see the same block.

Example with overrides:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas", "matplotlib"]
#
# [tool.jellycell]
# timeout_seconds = 1200     # override run.timeout_seconds for this file
# ///
```

## Cell markers

Jupytext percent format:

| Marker                                 | Cell type                        |
| -------------------------------------- | -------------------------------- |
| `# %%`                                 | Code cell (untagged)             |
| `# %% tags=["jc.step", "name=foo"]`    | Code cell with tags              |
| `# %% [markdown]`                      | Markdown cell                    |
| `# %% [raw]`                           | Raw cell (rarely needed)         |

Cell source is everything between two `# %%` markers (or from the last marker
to end of file).

## Cell tags

The `tags=[...]` list on the marker line. Two classes of tags:

**Kind tags** — exactly one per cell. Untagged code cells default to `jc.step`.

| Kind         | Meaning                                              |
| ------------ | ---------------------------------------------------- |
| `jc.load`    | Loads input data (conventionally from `data/`)        |
| `jc.step`    | Default — transform, compute                          |
| `jc.figure`  | Writes an image artifact                              |
| `jc.table`   | Writes a tabular artifact                             |
| `jc.setup`   | No deps; not cached; runs first                       |
| `jc.note`    | Markdown-only; not executable                         |

**Attribute tags** — `key=value`:

| Attr               | Meaning                                           | Example         |
| ------------------ | ------------------------------------------------- | --------------- |
| `name=...`         | Cell's name. Referenceable via `deps=` elsewhere. | `name=summary`  |
| `deps=a,b,c`       | Explicit deps. Comma-separated list of names.     | `deps=raw,env`  |
| `timeout=N`        | Per-cell timeout in seconds                       | `timeout=60`    |

Tags round-trip losslessly through jupytext — verified by tests.

## Cache-key semantics

A cell's cache key is `sha256(source, sorted_dep_keys, env_hash, minor_version)`:

- **`source`** — normalized (line endings `\n`; per-line trailing whitespace
  stripped; leading/trailing blank lines removed). So cosmetic edits don't
  invalidate the cache.
- **`sorted_dep_keys`** — the cache keys of every dep cell. Dep order doesn't
  matter; content does.
- **`env_hash`** — sha256 of the PEP-723 `dependencies` list (or the project's
  lockfile hash when that's wired up).
- **`MINOR_VERSION`** — jellycell's cache-key version counter. Bumps on
  cache/hashing algorithm changes ([§10.2 contract](reference/contracts.md)).
  Independent of the package semver.

Change any of these → cache miss → re-execute.

## Idempotent round-trip

`jellycell.format.parse` + `write` round-trip byte-exact for canonical
percent-format input. The PEP-723 block is preserved verbatim (jupytext's
default behavior would mutate it — jellycell strips and re-inserts).

A lint-clean file read + written twice produces no diff.

## Cell dataflow: artifacts vs in-memory

Cells can refer to values defined in earlier cells *in the same kernel
process*. That works when every cell in a run executes fresh. But **cached
cells do not re-execute** — their manifest is restored, not their code.

If notebook editing causes a partial cache invalidation (one cell changes,
its dependents don't), the runner will re-execute the changed cells in a
kernel where the *cached* cells' variables were never defined. Dependent
re-executed cells that reference those in-memory variables will fail with
`NameError`.

**Rule: inter-cell data goes through `jc.save` + `jc.load`.** That way the
value is persisted as an artifact, and any re-executed cell reads it back
from disk regardless of whether the producer ran or was a cache hit.

```python
# cell "raw"
df = pd.read_csv("data/input.csv")
jc.save(df, "artifacts/raw.parquet")

# cell "summary" with deps=raw — safe even if "raw" was cached
df = jc.load("artifacts/raw.parquet")
summary = df.describe()
```

The `jellycell run` CLI now warns when a single run mixes cache hits with
re-executions; that warning is your cue to double-check that downstream
cells use `jc.load` instead of reaching for variables in the kernel
namespace.

### Applying `[tool.jellycell]` overrides at runtime

A notebook's PEP-723 block may set a `[tool.jellycell]` table that overrides
project-level config at file scope. Supported keys:

| Key                      | Effect                                            |
| ------------------------ | ------------------------------------------------- |
| `project.name` / `name`  | Display name for this notebook                    |
| `run.kernel` / `kernel`  | Jupyter kernel override                           |
| `run.timeout_seconds` / `timeout_seconds` | Per-notebook cell timeout       |

Unknown keys raise a lint error — typos like `timeouts = 60` don't silently
no-op.
