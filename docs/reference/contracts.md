# §10 Contracts

Three cross-cutting promises jellycell makes to its users and agents.
Each is expensive to break silently — so breaking them is a deliberate
ceremony, documented below.

Bumping `__version__` follows the versioning policy in
[Releasing](../development/releasing.md); **every §10 break is a major
bump**.

## §10.1 — `--json` schemas

> Every CLI command supports `--json`. The shape of that JSON is a
> pydantic model with `schema_version: int`. Field renames, removals,
> and type changes are breaking.

**Stable across patches + minors:**

- Existing fields keep their names.
- Existing fields keep their types.
- `schema_version` stays the same.

**Allowed additively in minors** (no `schema_version` bump):

- Adding an optional field with a default.
- Adding a value to an enum (as long as it doesn't narrow consumers).

**Requires a major + `schema_version` bump:**

- Renaming a field.
- Removing a field.
- Changing a field's type in a non-widening way (e.g. `str → int`).
- Changing the shape of a nested object.

### Owning models

Each command's `--json` output has one pydantic model as the source of
truth. Adding `schema_version: int = 1` is required.

| Command                      | Model                                         |
| ---------------------------- | --------------------------------------------- |
| `jellycell init`             | `cli.commands.init.InitReport`                |
| `jellycell lint`             | `cli.commands.lint.LintReport`                |
| `jellycell run`              | `run.runner.RunReport`                        |
| `jellycell render`           | `cli.commands.render.RenderReport`            |
| `jellycell cache list`       | `cli.commands.cache.CacheListReport`          |
| `jellycell cache clear`      | `cli.commands.cache.CacheClearReport`         |
| `jellycell cache prune`      | `cli.commands.cache.CachePruneReport`         |
| `jellycell cache rebuild-index` | `cli.commands.cache.CacheRebuildReport`    |
| `jellycell export ipynb/md/tearsheet` | `cli.commands.export.ExportReport`   |
| `jellycell new`              | `cli.commands.new.NewReport`                  |
| (manifest file format)       | `cache.manifest.Manifest`                     |

### Regression

Every `--json` command's shape is pinned by
`tests/integration/test_json_schemas.py`. Snapshots live alongside the
test under `test_json_schemas/`. Regenerating a snapshot **must**
accompany a CHANGELOG entry + version bump level appropriate to the
change (additive = minor, shape change = major).

### Ceremony — when you change a `--json` model

1. Classify the change (additive vs. shape-change) per the rules above.
2. If breaking: increment `schema_version` in the pydantic model (1 → 2).
3. Regenerate the snapshot:
   ```bash
   uv run pytest tests/integration/test_json_schemas.py --force-regen
   ```
4. Bump `__version__` in `src/jellycell/_version.py` to the appropriate level.
5. Add a `CHANGELOG.md` entry under the new version.
6. In the PR, note "Invariant touched: §10.1 (`<model>`)" and the
   before/after shape.

---

## §10.2 — Cache key algorithm

> A cell's cache key is a pure function of `(normalized source,
> sorted dep keys, env_hash, MINOR_VERSION)`. Any change to *what* goes
> in or *how* it's combined forces every existing cache entry to
> invalidate cleanly.

Lives in `src/jellycell/cache/hashing.py`. The algorithm and
`MINOR_VERSION` are a single joint contract.

### What's in the key

- **Normalized source** — line endings → `\n`, trailing whitespace
  stripped per-line, leading/trailing blank lines removed. Cosmetic
  edits don't invalidate.
- **Sorted dep keys** — the cache keys of the cells this one depends on
  (declared explicitly via `deps=` tag, via `jc.deps(...)` AST-walked
  out of source, or via producer lookup on `jc.load(...)`). Order
  doesn't matter; content does.
- **`env_hash`** — sha256 of the lockfile (`uv.lock` / `poetry.lock`)
  bytes if present, otherwise of the PEP-723 `dependencies` list.
- **`MINOR_VERSION`** — the counter in `src/jellycell/_version.py`
  baked into every key. Bumping it invalidates the entire cache in one
  move.

### `MINOR_VERSION` is not semver

It's a separate counter. Independent of `__version__`. Bump whenever:

- `cache/hashing.py` changes behavior (normalization, what goes in,
  how it's combined).
- Any pydantic schema baked into a manifest gains or renames a field.

### Regression

`tests/unit/test_hashing.py` pins concrete key values for canonical
inputs. Any change to the algorithm fails the snapshot by design.

### Ceremony — when you change the algorithm

1. Bump `MINOR_VERSION` in `_version.py` by 1, and add a dated one-liner
   in the docstring explaining what changed.
2. Regenerate the snapshot:
   ```bash
   uv run pytest tests/unit/test_hashing.py --force-regen
   ```
3. Bump `__version__` to the next major (`1.X.Y → 2.0.0`) — cache
   invalidation is breaking.
4. Add a `CHANGELOG.md` entry under the new version, prominently noting
   the one-shot invalidation.
5. Run `/spec-check` to confirm the ceremony before merging.

---

## §10.3 — Agent guide content

> The markdown emitted by `jellycell prompt` is the canonical agent
> guide. Agents rely on it as a stable bootstrap; changes that modify
> existing guidance break their flow.

Content lives in `docs/agent-guide.md` and is packaged + emitted via
`src/jellycell/cli/commands/prompt.py`.

### What's stable

- Every documented rule keeps its meaning across patches.
- The CLI command table is accurate.
- The "idiomatic patterns" section doesn't drop rules without ceremony.

### Three-tier classification

- **Typo / clarification** (no meaning change) → **patch** bump is fine.
- **Additive** (new section for a new feature; existing sections
  unchanged) → **minor** bump.
- **Breaking** (existing guidance removed, rewritten with different
  meaning, or changed in a way that would mislead an agent following
  the previous version) → **major** bump.

### Regression

`tests/unit/test_prompt_snapshot.py` captures the full output. Any
content change fails the snapshot; regenerate intentionally and add a
CHANGELOG note.

### Ceremony — when you change the agent guide

1. Classify the change (typo / additive / breaking).
2. Regenerate the snapshot:
   ```bash
   uv run pytest tests/unit/test_prompt_snapshot.py --force-regen
   ```
3. Bump `__version__` per the tier.
4. Add a `CHANGELOG.md` entry.
5. In the PR, note "Invariant touched: §10.3" and the classification.

---

## Summary

| §     | Contract                    | File                                     | Regression snapshot                                           |
| ----- | --------------------------- | ---------------------------------------- | ------------------------------------------------------------- |
| 10.1  | `--json` schemas            | pydantic models with `schema_version`    | `tests/integration/test_json_schemas/`                        |
| 10.2  | Cache key algorithm         | `src/jellycell/cache/hashing.py`         | `tests/unit/test_hashing/`                                    |
| 10.3  | Agent guide content         | `docs/agent-guide.md`, `cli/commands/prompt.py` | `tests/unit/test_prompt_snapshot/`                      |

The `/spec-check` slash command and the `spec-reviewer` subagent both
read this page when auditing a diff.

## See also

- [Architecture](architecture.md) — the 8-layer boundary that the
  contracts sit on top of.
- [Releasing](../development/releasing.md) — the full versioning
  policy, including the patch/minor/major decision rule.
