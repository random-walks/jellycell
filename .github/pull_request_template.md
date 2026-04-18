<!--
Thanks for contributing! Please fill in the sections below.
See CONTRIBUTING.md for the full PR checklist.
-->

## Summary

<!-- One paragraph: what changes and why. -->

## Type

- [ ] `feat` — new feature
- [ ] `fix` — bug fix
- [ ] `docs` — docs only
- [ ] `refactor` — no behavior change
- [ ] `test` — tests only
- [ ] `chore` — tooling, CI, release

## Version bump

<!-- jellycell prefers frequent small bumps. See docs/development/releasing.md. -->

- [ ] patch (`1.0.X`) — bug fix / refactor / docs / non-user-visible plumbing (default)
- [ ] minor (`1.X.0`) — new CLI flag / new `jc.*` function / new config key / additive `--json` field
- [ ] major (`X.0.0`) — §10 contract break (cache key / agent-guide content / breaking `--json` schema)

`__version__` bumped in `_version.py` and `CHANGELOG.md` updated under the new heading? If not, explain why.

## Area / budget

<!-- Which v0 spec §8 area does this touch? Does the phase's src file budget still hold? -->

- Area (phase): <!-- 0 / 1 / 2 / ... -->
- File count after this PR: `src/jellycell/<subdir>/` has N files (budget M).

## Invariant check (§10 — see docs/reference/contracts.md)

Does this PR touch any of the three cross-cutting contracts?

- [ ] **`--json` schemas** (any pydantic model with `schema_version`)
- [ ] **Cache key algorithm** (`src/jellycell/cache/hashing.py`, `_version.py`)
- [ ] **Agent guide content** (`cli/commands/prompt.py`, `docs/agent-guide.md`)

If any are checked, describe the ceremony followed:

<!--
- For cache key changes: MINOR_VERSION bumped? test_hashing snapshot regenerated? Major version bump? CHANGELOG entry?
- For --json schema changes: schema_version incremented (breaking only)? Parsers updated? CHANGELOG entry?
- For agent guide changes: classified correctly (typo=patch, additive=minor, breaking=major)? prompt snapshot regenerated? CHANGELOG entry?
-->

## Testing

- [ ] `make lint` passes
- [ ] `make test` passes
- [ ] `make docs-build` passes (`sphinx-build -W`)
- [ ] New public functions have docstrings

## Notes for reviewer

<!-- Anything subtle, any design decisions worth calling out, linked issues. -->
