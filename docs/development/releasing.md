# Releasing

Releases go through **PyPI trusted publisher (OIDC)** — no stored API tokens.

## Versioning policy (post-1.0)

jellycell follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html), but leans **toward frequent small bumps** rather than batching changes into feature milestones. The goal: every merge to `main` can become a release. If a change is worth merging, it is worth a version.

### Which bump?

- **Patch (`1.0.X`)** — the default. Bug fixes, docs, refactors, non-user-visible plumbing, additive tests, new examples, dependency bumps with no observable behavior change. **Bump patch on every merge unless the change meets one of the conditions below.** Patch releases should feel cheap — batching many small fixes into one patch is fine and encouraged; batching them into "the next minor" is not.

- **Minor (`1.X.0`)** — user-visible additive changes only: new CLI commands or flags, new `jc.*` API functions, new config keys, new lint rules. The existing surface must continue to work unchanged. No breaking changes. No cache-key changes. No schema renames.

- **Major (`X.0.0`)** — breaking changes to one of the three §10 contracts, and only those. Other breaking changes (removing a private internal module, changing an undocumented default) still go in a minor or patch; the §10 contracts are the only things that force a major.

### What forces a major bump (§10 contracts)

1. **`--json` schema** shape changes that break existing parsers. Renaming a field, removing a field, or changing a type is breaking. Adding an optional field is additive — bump minor.
2. **Cache key algorithm** changes (anything in `cache/hashing.py`). These force every cache to invalidate; a major bump is honest signalling. You **must also** bump `MINOR_VERSION` in `_version.py` and regenerate `tests/unit/test_hashing.py` so the regression snapshot captures the new hashes.
3. **Agent guide content** (`jellycell prompt` output) — what agents in the wild depend on. **Breaking content edits** (existing guidance removed, rewritten with different meaning, or changed in a way that would mislead an agent following the previous version) force a major. **Additive content** (a new section for a new feature without touching existing sections) is a minor. **Typo fixes and clarifications** are patches.

### What's cheap and should not wait

- A docs typo fix → patch. Merge. Release.
- Adding a `--limit N` flag to `jellycell cache list` → minor.
- Fixing a bug where the live viewer crashes on empty notebooks → patch.
- Adding a new lint rule behind a config flag → minor.
- Tightening an internal type → patch.

If you find yourself writing "we'll ship this in the next big release," you're thinking about it wrong. Cut a patch.

## One-time setup (completed before `1.0.0`)

1. Register `jellycell` on PyPI (empty project, owned by maintainer account).
2. On PyPI, under the project: **Publishing → Trusted Publishers → Add** with:
   - Owner: `random-walks`
   - Repository: `jellycell`
   - Workflow: `release.yml`
   - Environment: `pypi`
3. On GitHub: **Settings → Environments → New environment** named `pypi`. Optionally add a protection rule for "Required reviewers" so tag pushes need manual approval.
4. Park placeholder projects `jellycell-cli` and `jellycell-server` on PyPI to prevent name squatting.

## Cutting a release

1. **Update `CHANGELOG.md`** — move `[Unreleased]` items under a new version heading, add a release date. One-line bullets are fine for patches.
2. **Bump `__version__`** in `src/jellycell/_version.py`. Match the version level to the change (see policy above).
3. **If the cache-key algorithm changed**, bump `MINOR_VERSION` in the same file and regenerate `tests/unit/test_hashing.py` (`pytest tests/unit/test_hashing.py --force-regen`). Note the change in the `_version.py` docstring so the history is traceable.
4. **If the agent guide content changed**, regenerate `tests/unit/test_prompt_snapshot.py` (`pytest tests/unit/test_prompt_snapshot.py --force-regen`). Note in the changelog.
5. **If any `--json` shape changed**, regenerate `tests/integration/test_json_schemas.py` snapshots — and confirm the change is additive (minor) vs breaking (major).
6. **Merge to `main`**, then tag:
   ```bash
   git tag v1.0.1
   git push --tags
   ```
7. **Watch the release workflow**. On success: wheel + sdist on PyPI, artifacts attached to the GitHub Release.

## Pre-release checklist

```bash
make lint
make test
make docs-build
make release-check       # builds sdist + wheel, prints version
```

All green? Tag and push.

## What can go wrong

- **OIDC mismatch**: trusted publisher config uses the wrong workflow filename or environment → PyPI rejects the upload. Fix: align PyPI publisher config to match `.github/workflows/release.yml`.
- **Name collision**: someone yanked a similar package and the namespace is reserved → contact PyPI support.
- **Build fails**: usually a version parse error in `_version.py` or a missing MANIFEST. Run `make release-check` locally first.
- **Snapshot regen forgotten**: CI catches this — a stale snapshot in `tests/unit/test_hashing.py` or `tests/integration/test_json_schemas/` will fail the job. Regenerate with `--force-regen` and commit.
