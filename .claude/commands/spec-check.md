---
description: Review current diff against jellycell §10 invariants.
---

Run a focused review of the current working-tree diff against the three cross-cutting contracts in `docs/reference/contracts.md`.

## Steps

1. Read `docs/reference/contracts.md` for the authoritative contract definitions + the ceremony each change requires.
2. Run `git diff` and `git diff --staged` to see what changed.
3. For each of the three invariants, check whether the diff touches it:

### Invariant 1 — `--json` schemas (§10.1)

Files that matter: any pydantic model with a `schema_version` field, especially in:
- `src/jellycell/cli/commands/*.py` (command report models)
- `src/jellycell/cache/manifest.py`
- `src/jellycell/run/runner.py` (RunReport)

Ask: did a field get added/removed/renamed? Was `schema_version` bumped?

### Invariant 2 — Cache key algorithm (§10.2)

Files that matter:
- `src/jellycell/cache/hashing.py` — the algorithm itself
- `src/jellycell/_version.py` — where `MINOR_VERSION` lives
- `tests/unit/test_hashing.py` — the regression snapshot

Ask:
- Did `cache/hashing.py` change at all? If so, was `MINOR_VERSION` bumped in `_version.py`?
- Was the regression snapshot in `tests/unit/test_hashing.py` regenerated intentionally (and noted in CHANGELOG)?

### Invariant 3 — Agent guide content (§10.3)

Files that matter:
- `src/jellycell/cli/commands/prompt.py`
- `docs/agent-guide.md`

Ask: did either change? If so, is this a minor-version bump release (not a patch)? Is there a CHANGELOG note?

## Output

Report format:

```
SPEC CHECK

Invariant 1 (--json schemas): [clean | VIOLATED: <details>]
Invariant 2 (cache key):       [clean | VIOLATED: <details>]
Invariant 3 (agent guide):     [clean | VIOLATED: <details>]

Recommendation: [merge safe | needs ceremony first]
```

If any invariant is touched without the required ceremony, list the specific ceremony missing with file:line pointers. Reference `docs/reference/contracts.md` in the explanation.

If nothing in the diff touches any invariant, say so plainly in one line.
