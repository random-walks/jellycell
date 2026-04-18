---
name: phase-budget
description: Check against spec §8 phase file-count budgets before creating new files under src/jellycell/ or tests/. Prevents scope creep by treating drift as a cut-scope signal, not a raise-ceiling signal.
---

Each phase in `docs/spec/v0.md` §8 has a soft file-count budget per area of the codebase. Significant drift is a **scope-creep signal** — cut features or defer them, don't raise the ceiling.

## How to check

**First: run `/phase-status`.** That slash command counts `git ls-files 'src/jellycell/**/*.py'` grouped by phase and reports drift. It is the authoritative source. The table below is a reference snapshot.

## Snapshot as of v1.0.0 (April 2026)

| Phase | src .py | Budget | Drift | Notes                                                 |
| ----- | ------: | -----: | ----: | ----------------------------------------------------- |
| 0     |       3 |      3 |    =  | `__init__`, `__main__`, `_version`                    |
| 1     |      14 |     13 |   +1  | `cli/commands/__init__.py` counted (spec didn't)      |
| 2     |      16 |     13 |   +3  | Added `run/pool.py`, `run/env_hash.py`, `cache/function_cache.py` |
| 3     |       5 |     10 |   −5  | Templates/static live as subdir, not counted as .py   |
| 4     |       5 |      4 |   +1  | `cli/commands/view.py` counted                        |
| 5     |       4 |      3 |   +1  | `cli/commands/export.py` counted                      |
| 6     |       3 |      2 |   +1  | `format/static_deps.py` landed with agent-surface work|

Total: **~50 src .py files** (spec target was ~45 across all phases).

## When to use this skill

- About to create a new `src/jellycell/<phase-dir>/*.py`.
- About to create a new test under `tests/unit/` or `tests/integration/`.
- Reviewing a PR that adds multiple files.

## Decision rule

1. **First run `/phase-status`** — get the real count.
2. If drift ≤ +2: probably fine. Commit message should explain why the new file is necessary.
3. If drift > +2 or phase chronically over: STOP. Ask:
   - Is this genuinely within this phase's area, or has scope crept?
   - Could it go in a follow-up release?
   - Can existing files absorb the change instead of adding a new one?
4. Updating the table above is a **manual** step — do it as part of a patch release when counts drift, not as a drive-by edit.

## Anti-pattern

Do not interpret "the budget was close to exceeded so I expanded it" as a reasonable outcome. The phases were sized deliberately. Growth is a signal to cut.

## Reference

- `docs/spec/v0.md` §8 — the original phase descriptions + file-count budgets (frozen historical snapshot; numbers still used as scope-creep ceilings today).
- `docs/spec/v0.md` §9 — "Total scope" principle.
- `/phase-status` — live count command (always preferred over this table).
