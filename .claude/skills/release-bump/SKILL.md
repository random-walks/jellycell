---
name: release-bump
description: Use when finishing a user-visible change in jellycell to determine whether a version bump is warranted and what level (patch / minor / major). Reminds the agent of the project's lean-into-small-releases policy so changes don't accumulate in an unreleased pile.
---

jellycell prefers **frequent small releases** over accumulated feature batches. If a change is worth merging, it is worth a version bump. The policy lives in `docs/development/releasing.md` — this skill is the short reminder.

## When to invoke

After wrapping up any user-visible change (a bug fix, a new flag, a doc clarification) and before moving on — ask: does this warrant a bump? If yes, prepare the change as part of the same PR.

Do not skip the bump for "it's small." Patch bumps are the default; small is the point.

## Decision rule

1. Did the change touch one of the three §10 contracts in a way the `spec-invariant` skill considers breaking? → **major**.
2. Is the change a user-visible addition (new CLI flag, new `jc.*` function, new config key, new lint rule, new `--json` field that is optional/additive)? → **minor**.
3. Everything else (bug fixes, refactors, docs, tests, examples, CI, deps with no behavior change) → **patch**.

If in doubt, **patch**. Patch releases are cheap.

## What to do

1. Bump `__version__` in `src/jellycell/_version.py` to the chosen level.
2. Move entries from `[Unreleased]` in `CHANGELOG.md` under the new version heading with today's date.
3. If it's a major and the cache-key algorithm changed, the `spec-invariant` skill's §10.2 ceremony also applies (bump `MINOR_VERSION`, regen `tests/unit/test_hashing.py`).
4. Include the bump in the same commit or PR as the change — do not split "the fix" from "the version."

## What NOT to do

- Don't hoard changes in `[Unreleased]` waiting for "something big." Ship the patches.
- Don't raise major just because the change feels significant. Major is reserved for §10 contract breaks.
- Don't split the version bump into a separate PR from the change. One commit, one PR.

## Reference

- `docs/development/releasing.md` — full policy and the checklist for cutting a tag.
- `CHANGELOG.md` — the shape to match.
- `.claude/skills/spec-invariant/SKILL.md` — when the change is contract-breaking.
