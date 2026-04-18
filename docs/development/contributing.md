# Contributing

Full contribution guide lives at [CONTRIBUTING.md](https://github.com/random-walks/jellycell/blob/main/CONTRIBUTING.md) in the repo root. This page summarizes the key rules for first-time contributors.

## The three invariants

These are locked in [reference/contracts](../reference/contracts.md) (living) and [CLAUDE.md](https://github.com/random-walks/jellycell/blob/main/CLAUDE.md). Touching any of them requires explicit ceremony:

1. **`--json` output schemas** — every command's JSON output has `schema_version: 1`. Adding/removing/renaming a field is a breaking change. Schemas are pydantic models in the command's subpackage.

2. **Cache key algorithm** — in `src/jellycell/cache/hashing.py`. Changing any input to the hash (source normalization, dep-key sorting, env-hash components) bumps `MINOR_VERSION` in `src/jellycell/_version.py`. This forces every cache to invalidate on upgrade.

3. **Agent guide content** — what `jellycell prompt` emits. Agents rely on it for onboarding. Changes go in minor releases with a CHANGELOG note.

## Phase budgets

[v0 spec §8](../spec/v0.md#8-build-phases-sized-in-files) defines a file count per phase (historical snapshot, still used as scope-creep ceilings). If a phase's `src/jellycell/<phase>/` creeps past its budget, that's a **scope-creep signal** — cut back. Don't raise the ceiling.

## Piggyback first

Before writing new code for parsing, caching, file-watching, templating, or HTML output, check the [piggyback map in reference/architecture](../reference/architecture.md#piggyback-map). If a well-maintained lib already does it, use it.

## PR checklist

- [ ] `make lint` green (ruff, ruff format, mypy).
- [ ] `make test` green.
- [ ] `make docs-build` green (`sphinx-build -W` treats warnings as errors).
- [ ] Docstrings on all new public functions (D100–D103 enforced).
- [ ] "Invariant touched?" answered in PR description (yes/no + ceremony followed).
- [ ] Phase budget still respected.

## Claude Code skills

Three project-level skills live under `.claude/skills/` and encode §10
guardrails (see [reference/contracts](../reference/contracts.md)). Claude Code auto-discovers them from this path when the CLI
starts, but a running session does **not** pick up new or edited skills until
you restart it (`/exit` → `claude` again).

To verify loading:

1. Open a fresh Claude Code session in the repo.
2. Type `/` and scroll through the skill list — look for `spec-invariant`,
   `piggyback-first`, `phase-budget`.
3. If missing: check each `SKILL.md` has both `name:` and `description:` in
   frontmatter (no other fields are required).

Skills are plain markdown — edit freely. Keep the description specific and
action-oriented; vague descriptions dilute auto-triggering accuracy.
