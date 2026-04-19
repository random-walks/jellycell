"""Version and cache-key-version constants.

``__version__`` is the public semver string. Hatchling reads it for build
metadata. The versioning policy lives in
:doc:`docs/development/releasing.md` — tl;dr: **patch-bump freely, minor
for additive features, major only for breaking contracts**.

``MINOR_VERSION`` is a separate counter baked into the cache key so stale
entries invalidate cleanly when the hash algorithm changes. It is **not**
semver — it only moves when something in :mod:`jellycell.cache.hashing`
(normalization, which inputs go in, or how they're combined) changes, or
when a cached pydantic schema gains/renames a field.

See CLAUDE.md and spec §10 for the full contract.
"""

from __future__ import annotations

__version__ = "1.2.0"

MINOR_VERSION: int = 1
"""Spec §10.2 cache-key counter. Bump on any cache/hashing behavior change.

Post-1.0 bumps should be rare and each one gets a one-line note below with
the date and what changed — so future agents can trace the history.

- v1 (2026-04-18, initial): source + sorted dep keys + env_hash (lockfile
  preferred, PEP-723 fallback) + MINOR_VERSION.
"""
