"""Content-addressed cache for jellycell cell executions.

Exports:
    - :mod:`jellycell.cache.hashing` — key derivation (§10.2 contract).
    - :class:`Manifest` / :class:`OutputRecord` / :class:`ArtifactRecord`
      — on-disk manifest schema.
    - :class:`CacheStore` — the blob + manifest store.
    - :class:`CacheIndex` — the SQLite catalogue accelerator.
"""

from __future__ import annotations

from jellycell.cache.hashing import env_hash_from_deps, key, normalize_source, source_hash
from jellycell.cache.index import CacheIndex
from jellycell.cache.manifest import ArtifactRecord, Manifest, OutputRecord
from jellycell.cache.store import CacheStore

__all__ = [
    "ArtifactRecord",
    "CacheIndex",
    "CacheStore",
    "Manifest",
    "OutputRecord",
    "env_hash_from_deps",
    "key",
    "normalize_source",
    "source_hash",
]
