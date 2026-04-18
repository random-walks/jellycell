"""SQLite catalogue accelerator for the cache.

The filesystem is the source of truth; this index is a derived accelerator
for the catalogue page (spec §2.3). :meth:`CacheIndex.rebuild_from_store`
re-scans all manifests to repair corruption.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from types import TracebackType
from typing import Any

from jellycell.cache.manifest import Manifest
from jellycell.cache.store import CacheStore

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cells (
    cache_key TEXT PRIMARY KEY,
    notebook TEXT NOT NULL,
    cell_id TEXT NOT NULL,
    cell_name TEXT,
    executed_at TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    status TEXT NOT NULL,
    manifest_path TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cells_notebook ON cells (notebook);

CREATE TABLE IF NOT EXISTS artifacts (
    sha256 TEXT NOT NULL,
    path TEXT NOT NULL,
    size INTEGER NOT NULL,
    mime TEXT,
    producer_cache_key TEXT NOT NULL,
    PRIMARY KEY (sha256, path)
);
CREATE INDEX IF NOT EXISTS idx_artifacts_producer
    ON artifacts (producer_cache_key);
"""


class CacheIndex:
    """SQLite accelerator over the manifest directory."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def insert(self, manifest: Manifest, manifest_path: Path) -> None:
        """Upsert a manifest into the index."""
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO cells "
                "(cache_key, notebook, cell_id, cell_name, executed_at, "
                " duration_ms, status, manifest_path) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    manifest.cache_key,
                    manifest.notebook,
                    manifest.cell_id,
                    manifest.cell_name,
                    manifest.executed_at.isoformat(),
                    manifest.duration_ms,
                    manifest.status,
                    str(manifest_path),
                ),
            )
            self._conn.execute(
                "DELETE FROM artifacts WHERE producer_cache_key = ?",
                (manifest.cache_key,),
            )
            for art in manifest.artifacts:
                self._conn.execute(
                    "INSERT OR REPLACE INTO artifacts "
                    "(sha256, path, size, mime, producer_cache_key) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (art.sha256, art.path, art.size, art.mime, manifest.cache_key),
                )

    def list_by_notebook(self, notebook: str) -> list[dict[str, Any]]:
        """Return all cell entries for a given notebook path (relative)."""
        cur = self._conn.execute(
            "SELECT cache_key, cell_id, cell_name, executed_at, duration_ms, status "
            "FROM cells WHERE notebook = ? ORDER BY executed_at",
            (notebook,),
        )
        cols = ("cache_key", "cell_id", "cell_name", "executed_at", "duration_ms", "status")
        return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]

    def notebook_view_key(self, project_root: Path, notebook_rel: str) -> str | None:
        """Hash of everything that affects the rendered view of a notebook.

        The live viewer uses this as its response-cache key. Captures both
        **source edits** (the notebook file's bytes) and **manifest changes**
        (the ordered set of cell cache keys), so either kind of change
        invalidates the cached HTML cleanly.

        Returns a hex sha256 string, or ``None`` when the notebook file is
        missing — the caller should skip caching in that case and let the
        404 path render naturally.
        """
        nb_path = project_root / notebook_rel
        try:
            nb_bytes = nb_path.read_bytes()
        except (OSError, FileNotFoundError):
            return None
        source_hash = hashlib.sha256(nb_bytes).hexdigest()
        cell_keys = [str(row["cache_key"]) for row in self.list_by_notebook(notebook_rel)]
        combined = source_hash + "|" + ",".join(sorted(cell_keys))
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def find_producer(self, artifact_path: str) -> dict[str, Any] | None:
        """Look up which cell produced an artifact at ``artifact_path``.

        Returns a dict with ``cache_key``, ``notebook``, ``cell_id``,
        ``cell_name`` for the most recent producer, or ``None`` if no manifest
        references this path.

        Used by :func:`jellycell.api.load` to register implicit dep edges, and
        by the UI to display "which cell produced this file?".
        """
        cur = self._conn.execute(
            "SELECT c.cache_key, c.notebook, c.cell_id, c.cell_name "
            "FROM artifacts a "
            "JOIN cells c ON a.producer_cache_key = c.cache_key "
            "WHERE a.path = ? "
            "ORDER BY c.executed_at DESC "
            "LIMIT 1",
            (artifact_path,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "cache_key": row[0],
            "notebook": row[1],
            "cell_id": row[2],
            "cell_name": row[3],
        }

    def list_all(self) -> list[dict[str, Any]]:
        """Return every indexed cell, newest first."""
        cur = self._conn.execute(
            "SELECT cache_key, notebook, cell_id, cell_name, executed_at, duration_ms, status "
            "FROM cells ORDER BY executed_at DESC"
        )
        cols = (
            "cache_key",
            "notebook",
            "cell_id",
            "cell_name",
            "executed_at",
            "duration_ms",
            "status",
        )
        return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]

    def rebuild_from_store(self, store: CacheStore) -> int:
        """Re-scan all manifests from ``store``. Returns the count indexed."""
        with self._conn:
            self._conn.execute("DELETE FROM cells")
            self._conn.execute("DELETE FROM artifacts")
        count = 0
        for manifest in store.iter_manifests():
            self.insert(manifest, store.manifest_path(manifest.cache_key))
            count += 1
        return count

    def clear(self) -> None:
        """Empty the index. Does not touch manifests on disk."""
        with self._conn:
            self._conn.execute("DELETE FROM cells")
            self._conn.execute("DELETE FROM artifacts")

    def close(self) -> None:
        """Close the underlying connection."""
        self._conn.close()

    def __enter__(self) -> CacheIndex:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
