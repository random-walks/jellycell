# Contributing to jellycell

Read this page before opening a PR.

## Before you start

1. **Read [`docs/reference/`](docs/reference/index.md)** — the living authoritative reference:
   - [architecture](docs/reference/architecture.md) — piggyback map (libraries we depend on and what they do for us) + 8-layer dependency order.
   - [contracts](docs/reference/contracts.md) — the three §10 cross-cutting contracts with their ceremonies.
2. Phase file-count budgets live in [`docs/spec/v0.md`](docs/spec/v0.md) §8 as a historical snapshot — still used as scope-creep ceilings today.
3. **Read [`CLAUDE.md`](CLAUDE.md)** for the tl;dr of architecture rules.
4. Open an issue for anything non-trivial before writing code. A short discussion up front saves a long re-review later.

## Local setup

Full guide: [docs/development/dev-setup.md](docs/development/dev-setup.md). Quick version:

```bash
git clone https://github.com/random-walks/jellycell
cd jellycell
make dev       # uv sync + pre-commit install
make test      # pytest
```

## Dev loop

```bash
make test             # full test suite
make test-unit        # fast tests only
make lint             # ruff + mypy
make format           # apply ruff formatting + autofix
make docs             # live-reload docs at :8001
make docs-build       # sphinx-build -W (CI-mirror)
```

## Invariants (DO NOT CHANGE SILENTLY)

Three contracts — living statement in [`docs/reference/contracts.md`](docs/reference/contracts.md), historical record in [v0 spec §10](docs/spec/v0.md#10-cross-cutting-contracts-lock-these-early). Touching any of them is a deliberate ceremony:

1. **`--json` output schemas.** Every command's JSON output carries `schema_version: 1`. Adding/removing/renaming a field bumps the schema version.

2. **Cache key algorithm** (`src/jellycell/cache/hashing.py`). Any change bumps `MINOR_VERSION` in `src/jellycell/_version.py`. Regression snapshot in `tests/unit/test_hashing.py`.

3. **Agent guide content** (`jellycell prompt` output). Typo/clarification edits are patch-safe; additive content is a minor; breaking changes to existing guidance force a major. See [docs/development/releasing.md](docs/development/releasing.md) for the full rule.

If you touched one of these, **say so explicitly** in the PR description and describe the ceremony you followed.

## Phase budgets

[v0 spec §8](docs/spec/v0.md#8-build-phases-sized-in-files) lists a soft file-count budget per area of the codebase. If an area creeps past its ceiling while you're extending it, that's a **scope-creep signal**. Cut features. Don't raise the ceiling.

## Versioning

jellycell prefers **frequent small bumps**: a bug fix → patch, a new additive feature → minor, a §10 contract break → major. Full policy in [docs/development/releasing.md](docs/development/releasing.md). Include the version bump in your PR, don't split it out.

## Commit style

[Conventional Commits](https://www.conventionalcommits.org/):

- `feat(cache): add cache rebuild-index CLI command`
- `fix(format): handle PEP-723 block with trailing whitespace`
- `docs: clarify agent guide stability contract`
- `refactor(run): extract Kernel context manager`
- `test(lint): cover pep723-position edge cases`

One commit per logical change. Rebase to clean history before merging when practical.

## Branch naming

- `feat/…`, `fix/…`, `docs/…`, `refactor/…`, `test/…`
- `agentic/…` optional prefix for AI-authored work.

## PR checklist

- [ ] `make lint` green.
- [ ] `make test` green.
- [ ] `make docs-build` green (`sphinx-build -W` — warnings are errors).
- [ ] New public functions have docstrings (ruff D100–D103 enforced).
- [ ] **"Invariant touched?"** — yes/no in the PR description. If yes, describe the ceremony followed.
- [ ] Phase budget respected (run `/phase-status` if using Claude Code).
- [ ] **Version bumped** in `src/jellycell/_version.py` matching the change (patch default; minor/major per policy).
- [ ] `CHANGELOG.md` updated under the version heading for user-visible changes.

## Reporting bugs

Use the [bug report issue template](.github/ISSUE_TEMPLATE/bug.md). Include:

- jellycell version (`jellycell --version` or `python -m jellycell --version`).
- Python version, OS.
- Minimal reproduction — notebook + command.
- Expected vs actual output.

## License

By contributing you agree your work is released under [Apache-2.0](LICENSE).
