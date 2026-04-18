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

## Phase

<!-- Which spec §8 phase does this touch? Is the phase's src file budget still respected? -->

- Phase: <!-- 0 / 1 / 2 / ... -->
- File count after this PR: `src/jellycell/<subdir>/` has N files (budget M).

## Invariant check (spec §10)

Does this PR touch any of the three cross-cutting contracts?

- [ ] **`--json` schemas** (any pydantic model with `schema_version`)
- [ ] **Cache key algorithm** (`src/jellycell/cache/hashing.py`, `_version.py`)
- [ ] **Agent guide content** (`cli/commands/prompt.py`, `docs/agent-guide.md`)

If any are checked, describe the ceremony followed:

<!--
- For cache key changes: MINOR_VERSION bumped? Regression snapshot updated? CHANGELOG entry?
- For --json schema changes: schema_version incremented? Downstream parsers updated? CHANGELOG entry?
- For agent guide changes: is this a minor-version release? CHANGELOG entry?
-->

## Testing

- [ ] `make lint` passes
- [ ] `make test` passes
- [ ] `make docs-build` passes (`sphinx-build -W`)
- [ ] New public functions have docstrings

## Notes for reviewer

<!-- Anything subtle, any design decisions worth calling out, linked issues. -->
