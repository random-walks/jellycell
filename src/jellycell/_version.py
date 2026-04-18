"""Version and spec-minor-version constants.

``__version__`` follows semver; hatchling reads it for build metadata.

``MINOR_VERSION`` is a component of the cache key (see spec §2.3 / §10.2).
BUMP IT whenever:

- :mod:`jellycell.cache.hashing` behavior changes (normalization,
  which inputs go into the hash, or how they're combined).
- Any pydantic JSON schema in the cache gains or renames a field.

This forces all caches to invalidate cleanly on upgrade. See CLAUDE.md
for the full ceremony.
"""

from __future__ import annotations

__version__ = "0.2.0"

MINOR_VERSION: int = 2
"""Spec §10.2 contract: cache-key minor version. Bump on behavior change.

v2 (this release):
  - Runner now resolves implicit deps from ``jc.load`` calls via the artifact
    lineage index.
  - Runner now AST-walks ``jc.deps("a", "b")`` calls statically so they enter
    the cache key before the cell runs (was: runtime-only, too late).
  - ``env_hash`` prefers lockfile (``uv.lock`` / ``poetry.lock``) bytes over
    the PEP-723 dependency list when available.

v1 (original):
  - Source + tag-declared deps + PEP-723-only env_hash + MINOR_VERSION.
"""
