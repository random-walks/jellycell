---
description: Bump the jellycell version for the change currently on this branch. Defaults to patch; argument overrides to `minor` or `major`.
---

Bump the jellycell version and move `[Unreleased]` changelog entries under the new heading. Use the argument (`patch`, `minor`, or `major`) or default to `patch`.

Argument (optional): `$ARGUMENTS`

## Steps

1. **Decide the level.** If the user passed `minor` or `major`, use it. Otherwise default to `patch` and tell the user what you chose. Consult `docs/development/releasing.md` for the decision rule if uncertain — but err toward patch.

2. **Read current `__version__`** in `src/jellycell/_version.py`.

3. **Compute the new version**:
   - patch: `MAJOR.MINOR.PATCH+1`
   - minor: `MAJOR.MINOR+1.0`
   - major: `MAJOR+1.0.0`

4. **Confirm contract ceremonies if major**:
   - If the cache-key algorithm changed (`cache/hashing.py` diff), bump `MINOR_VERSION` too and regenerate `tests/unit/test_hashing.py` snapshot (`uv run pytest tests/unit/test_hashing.py --force-regen`). Add a dated line in `_version.py` docstring.
   - If the `--json` schema changed in a breaking way, increment `schema_version` in the owning pydantic model and regenerate `tests/integration/test_json_schemas.py` snapshots.
   - If the agent guide content changed, regenerate `tests/unit/test_prompt_snapshot.py` snapshot.

5. **Edit `src/jellycell/_version.py`** to the new version string.

6. **Edit `CHANGELOG.md`**: move everything currently under `[Unreleased]` under a new `## [NEW_VERSION] — YYYY-MM-DD` heading. If `[Unreleased]` is empty, add a one-line entry describing the change on this branch. Update the comparison links at the bottom of the file.

7. **Run the pre-release checks**: `make lint && make test && make docs-build`. If anything fails, STOP and report. Do not commit a bump with red checks.

8. **Report** to the user:
   - The new version string
   - The level chosen and why
   - The checks run
   - Whether a tag push is the next step (or if they want to add more to the PR first)

## Do not

- Do not tag or push. The user tags after merge to `main`.
- Do not re-enter the §10 ceremony if the diff doesn't warrant it — a patch that touched zero contract files needs no snapshot regen.
- Do not split the bump into a separate commit unless the user asked; prefer including it with the change on the branch.
