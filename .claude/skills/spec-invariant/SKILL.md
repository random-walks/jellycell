---
name: spec-invariant
description: Follow this ceremony when editing spec §10 contract-protected files — src/jellycell/cache/hashing.py, src/jellycell/_version.py, src/jellycell/cli/commands/prompt.py, docs/agent-guide.md, docs/spec/v0.md, or any pydantic model carrying a schema_version field. Ensures cache invalidation, JSON schema versioning, and agent-guide stability are not breached silently.
---

You are about to touch a file governed by one of jellycell's three cross-cutting contracts (spec §10). These are "expensive to change later" — the ceremony here prevents silent drift.

## Which contract applies?

| If you're editing...                          | Contract             | Section |
| --------------------------------------------- | -------------------- | ------- |
| `src/jellycell/cache/hashing.py`              | Cache key algorithm  | §10.2   |
| `src/jellycell/_version.py`                   | Cache key algorithm  | §10.2   |
| Any pydantic model with `schema_version: int` | `--json` schema      | §10.1   |
| `src/jellycell/cli/commands/prompt.py`        | Agent guide content  | §10.3   |
| `docs/agent-guide.md`                         | Agent guide content  | §10.3   |
| `docs/spec/v0.md`                             | The spec itself      | all     |

## Ceremony

### Cache key changes (§10.2)

1. Bump `MINOR_VERSION` in `src/jellycell/_version.py` by 1.
2. Regenerate `tests/unit/test_hashing.py` regression snapshot:
   `uv run pytest tests/unit/test_hashing.py --regen-all`
3. Commit the regenerated snapshot file alongside the code change.
4. Add a `CHANGELOG.md` entry under `[Unreleased]`:
   `### Changed`
   `- Cache key algorithm: <what changed>. Existing caches invalidated.`
5. In the PR description, explain **why** the change is needed and what it breaks.

### `--json` schema changes (§10.1)

1. Increment `schema_version` in the pydantic model (1 → 2, 2 → 3, etc.).
2. Update the corresponding docs page (`docs/cli-reference.md`) if the shape is user-visible.
3. Search for downstream consumers: `rg 'schema_version' tests/ src/` — update parsers that hard-code `== 1`.
4. Add a `CHANGELOG.md` entry under `### Changed` with before/after example.

### Agent guide changes (§10.3)

1. Confirm this is a minor-version release (`0.N.0`), not a patch (`0.N.1`). Patches cannot change the agent guide.
2. If bumping from patch to minor, update `_version.py` accordingly.
3. Add `CHANGELOG.md` entry:
   `### Changed`
   `- Agent guide: <short summary>. Agents using a previous version may need updates.`

## After the change

Run `/spec-check` on the resulting diff to confirm the ceremony was complete. The `spec-reviewer` subagent will verify each invariant and report any missing steps.

## Reference

- `CLAUDE.md` — one-paragraph summary of each invariant.
- `docs/spec/v0.md` §10 — authoritative contract text.
- `docs/development/releasing.md` — how version bumps flow into a release.
