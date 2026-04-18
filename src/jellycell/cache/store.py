"""Cache store — blob store (via :mod:`diskcache`) plus manifest JSON files.

Filesystem is the source of truth. SQLite index (:mod:`jellycell.cache.index`)
is a derived accelerator. Layout (spec §2.3)::

    .jellycell/cache/
    ├── blobs/                    # diskcache — content-addressed binary blobs
    ├── manifests/<cache-key>.json
    └── state.db                  # SQLite index (see index.py)
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import TracebackType

import diskcache

from jellycell.cache.manifest import Manifest


class CacheStore:
    """Combined blob + manifest store for a project's ``.jellycell/cache/``.

    Usable as a context manager for clean ``diskcache`` teardown.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.blobs_dir = root / "blobs"
        self.manifests_dir = root / "manifests"
        self.blobs_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        self._disk = diskcache.Cache(
            str(self.blobs_dir),
            eviction_policy="none",
            size_limit=2**40,  # 1 TB soft limit; no eviction regardless
        )

    # ------------------------------------------------------------------ blobs
    def put_blob(self, data: bytes) -> str:
        """Store raw bytes; return sha256 hex digest (the blob key)."""
        digest = hashlib.sha256(data).hexdigest()
        self._disk.set(digest, data)
        return digest

    def get_blob(self, digest: str) -> bytes:
        """Fetch a blob by its sha256 digest. Raises KeyError if missing."""
        data = self._disk.get(digest)
        if data is None:
            raise KeyError(digest)
        if not isinstance(data, bytes):
            raise TypeError(f"Unexpected blob type: {type(data).__name__}")
        return data

    def has_blob(self, digest: str) -> bool:
        """Check whether a blob exists."""
        return digest in self._disk

    # --------------------------------------------------------------- manifest
    def manifest_path(self, cache_key: str) -> Path:
        """The on-disk path for a cache key's manifest."""
        return self.manifests_dir / f"{cache_key}.json"

    def put_manifest(self, manifest: Manifest) -> Path:
        """Write the manifest; return its on-disk path."""
        path = self.manifest_path(manifest.cache_key)
        manifest.write(path)
        return path

    def get_manifest(self, cache_key: str) -> Manifest:
        """Read the manifest for a cache key. Raises if missing."""
        path = self.manifest_path(cache_key)
        if not path.exists():
            raise KeyError(cache_key)
        return Manifest.read(path)

    def has(self, cache_key: str) -> bool:
        """Whether a manifest exists for this cache key."""
        return self.manifest_path(cache_key).exists()

    def iter_manifests(self) -> list[Manifest]:
        """All manifests in insertion-free order (by filename)."""
        return [Manifest.read(p) for p in sorted(self.manifests_dir.glob("*.json"))]

    # --------------------------------------------------------------- lifetime
    def close(self) -> None:
        """Close the backing diskcache. Idempotent."""
        self._disk.close()

    def __enter__(self) -> CacheStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
