---
description: Report src file counts per phase against spec §8 budgets.
---

Count source files under `src/jellycell/` organized by phase, compare against the budgets in `docs/spec/v0.md` §8, and report status.

## Steps

1. Enumerate files:
   - Phase 0 files (root): `src/jellycell/__init__.py`, `__main__.py`, `_version.py` — budget **3** src files (15 total repo-wide).
   - Phase 1 files: `src/jellycell/config.py`, `src/jellycell/paths.py`, `src/jellycell/format/**`, `src/jellycell/lint/**`, `src/jellycell/cli/__init__.py`, `src/jellycell/cli/app.py`, `src/jellycell/cli/commands/{__init__,init,lint}.py` — budget **13** src files.
   - Phase 2 files: `src/jellycell/api.py`, `src/jellycell/cache/**`, `src/jellycell/run/**`, `src/jellycell/cli/commands/{run,cache}.py` — budget **13** src files.
   - Phase 3 files: `src/jellycell/render/**`, `src/jellycell/cli/commands/render.py` — budget **10** src files.
   - Phase 4 files: `src/jellycell/server/**`, `src/jellycell/cli/commands/view.py` — budget **4** src files.
   - Phase 5 files: `src/jellycell/export/**`, `src/jellycell/cli/commands/export.py` — budget **3** src files.
   - Phase 6 files: `src/jellycell/cli/commands/{prompt,new}.py` — budget **2** new src files (plus doc/example modifications).

   Use `git ls-files 'src/jellycell/**/*.py'` for accuracy (don't count cached `.pyc`).

2. For each phase, compute: present / budget / status (✅ within, ⚠️ at budget, ❌ over).

3. Also count tests per phase at the `tests/` level and tag unreleased commits since the last tagged release.

## Output

Print a table:

```
PHASE STATUS (against docs/spec/v0.md §8)

Phase | src present | budget | status
------|-------------|--------|-------
0     |      3      |   3    |   ✅
1     |     14      |  13    |   ⚠️  (+1)
2     |     16      |  13    |   ❌ (+3)
...

Unreleased commits since v1.0.0: N
Current branch: main
Last tag: v1.0.0
```

If any phase is over budget, flag it prominently and remind: **"Over budget = scope-creep signal. Cut back; do not raise the ceiling."**
