# Releasing

Releases go through **PyPI trusted publisher (OIDC)** — no stored API tokens.

## One-time setup (done before v0.0.1)

1. Register `jellycell` on PyPI (empty project, owned by maintainer account).
2. On PyPI, under the project: **Publishing → Trusted Publishers → Add** with:
   - Owner: `random-walks`
   - Repository: `jellycell`
   - Workflow: `release.yml`
   - Environment: `pypi`
3. On GitHub: **Settings → Environments → New environment** named `pypi`. Optionally add a protection rule for "Required reviewers" so tag pushes need manual approval.
4. Park placeholder projects `jellycell-cli` and `jellycell-server` on PyPI to prevent name squatting.

## Cutting a release

1. **Update `CHANGELOG.md`** — move `[Unreleased]` items under a new version heading, add a release date.
2. **Bump version** in `src/jellycell/_version.py`:
   - Patch (`0.0.1 → 0.0.2`): no breaking changes, no cache-key changes.
   - Minor (`0.1.0 → 0.2.0`): breaking changes or cache-key changes (also bump `MINOR_VERSION`).
   - Major (`1.0.0 → 2.0.0`): reserved for post-v1.
3. **If the cache-key algo changed**, confirm `MINOR_VERSION` was bumped and `tests/unit/test_hashing.py` regression snapshot was regenerated with a changelog note.
4. **If the agent guide content changed**, confirm this is a minor release (not patch) and a changelog note exists.
5. **Merge to main**, then tag:
   ```bash
   git tag v0.0.2
   git push --tags
   ```
6. **Watch the release workflow**. On success: wheel + sdist on PyPI, artifacts attached to the GitHub Release.

## What can go wrong

- **OIDC mismatch**: trusted publisher config uses the wrong workflow filename or environment → PyPI rejects the upload. Fix: align PyPI publisher config to match `.github/workflows/release.yml`.
- **Name collision**: someone yanked a similar package and the namespace is reserved → contact PyPI support.
- **Build fails**: usually version parse error in `_version.py` or missing MANIFEST. Run `make release-check` locally first.

## Pre-release checklist

```bash
make lint
make test
make docs-build
make release-check       # builds sdist + wheel, prints version
```

All green? Tag and push.
