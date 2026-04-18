---
name: spec-invariant
description: Follow this ceremony when editing spec §10 contract-protected files — src/jellycell/cache/hashing.py, src/jellycell/_version.py, src/jellycell/cli/commands/prompt.py, docs/agent-guide.md, docs/spec/v0.md, or any pydantic model carrying a schema_version field. Ensures cache invalidation, JSON schema versioning, and agent-guide stability are not breached silently.
---

You are about to touch a file governed by one of jellycell's three cross-cutting contracts (spec §10). These are "expensive to change later" — the ceremony here prevents silent drift.

## Which contract applies?

| If you're editing...                          | Contract             | Section |
| --------------------------------------------- | -------------------- | ------- |
| `src/jellycell/cache/hashing.py`              | Cache key algorithm  | §10.2   |
| `src/jellycell/_version.py` MINOR_VERSION     | Cache key algorithm  | §10.2   |
| Any pydantic model with `schema_version: int` | `--json` schema      | §10.1   |
| `src/jellycell/cli/commands/prompt.py`        | Agent guide content  | §10.3   |
| `docs/agent-guide.md`                         | Agent guide content  | §10.3   |
| `docs/spec/v0.md`                             | The spec itself      | all     |

## Ceremony

### Cache key changes (§10.2)

Cache-key changes are **major** bumps — every existing cached result invalidates. Don't do this lightly.

1. Bump `MINOR_VERSION` in `src/jellycell/_version.py` by 1, and add a dated one-liner in the docstring explaining what changed.
2. Regenerate the hashing regression snapshot:
   ```
   uv run pytest tests/unit/test_hashing.py --force-regen
   ```
3. Commit the regenerated snapshot file alongside the code change.
4. Bump the semver **major** (`X.0.0`) in `_version.py::__version__` as well — cache invalidation is breaking.
5. Add a `CHANGELOG.md` entry under `[Unreleased]` in the `### Changed` section with "Cache key algorithm: <what changed>. Existing caches invalidated."
6. In the PR description, explain **why** the change is needed.

### `--json` schema changes (§10.1)

- **Additive** (new optional field) → **minor bump** (`1.X.0`). Keep `schema_version` unchanged; add the field to the pydantic model; document in `docs/cli-reference.md`.
- **Breaking** (field removed, renamed, or type-changed) → **major bump** (`X.0.0`). Increment `schema_version` in the owning model (1 → 2). Search for downstream consumers: `rg 'schema_version' tests/ src/` — update parsers that hard-code `== 1`.
- Regenerate `tests/integration/test_json_schemas.py` snapshots with `--force-regen`.
- Add a `CHANGELOG.md` entry with a before/after example.

### Agent guide changes (§10.3)

- **Typo / clarification** (no meaning change) → **patch**.
- **Additive** (new section for a new feature; existing sections unchanged) → **minor**.
- **Breaking** (existing guidance removed, rewritten with different meaning, or changed in a way that would mislead an agent following the previous version) → **major** (`X.0.0`). Agents in the wild depend on this output.
- Any regen of `tests/unit/test_prompt_snapshot.py` must accompany a CHANGELOG entry.

## After the change

Run `/spec-check` on the resulting diff to confirm the ceremony was complete. The `spec-reviewer` subagent will verify each invariant and report any missing steps.

## Reference

- `CLAUDE.md` — one-paragraph summary of each invariant.
- `docs/reference/contracts.md` — living authoritative contract text + ceremonies.
- `docs/spec/v0.md` §10 — frozen genesis statement (historical).
- `docs/development/releasing.md` — versioning policy + release workflow.
