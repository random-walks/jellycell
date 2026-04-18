"""Unit tests for jellycell.cache.store."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from jellycell.cache.manifest import Manifest
from jellycell.cache.store import CacheStore


def _manifest(cache_key: str) -> Manifest:
    return Manifest(
        cache_key=cache_key,
        notebook="n.py",
        cell_id="n:0",
        source_hash="s" * 64,
        env_hash="e" * 64,
        executed_at=datetime(2026, 4, 17, tzinfo=UTC),
        duration_ms=10,
        status="ok",
    )


class TestBlobs:
    def test_put_and_get(self, tmp_path: Path) -> None:
        with CacheStore(tmp_path) as store:
            digest = store.put_blob(b"hello")
            assert store.get_blob(digest) == b"hello"

    def test_put_is_content_addressed(self, tmp_path: Path) -> None:
        with CacheStore(tmp_path) as store:
            d1 = store.put_blob(b"same")
            d2 = store.put_blob(b"same")
            assert d1 == d2

    def test_get_missing_raises(self, tmp_path: Path) -> None:
        with CacheStore(tmp_path) as store, pytest.raises(KeyError):
            store.get_blob("missing" + "x" * 58)

    def test_has_blob(self, tmp_path: Path) -> None:
        with CacheStore(tmp_path) as store:
            digest = store.put_blob(b"x")
            assert store.has_blob(digest)


class TestManifests:
    def test_put_and_get(self, tmp_path: Path) -> None:
        store = CacheStore(tmp_path)
        try:
            m = _manifest("k" * 64)
            store.put_manifest(m)
            assert store.has(m.cache_key)
            assert store.get_manifest(m.cache_key) == m
        finally:
            store.close()

    def test_get_missing_raises(self, tmp_path: Path) -> None:
        store = CacheStore(tmp_path)
        try:
            with pytest.raises(KeyError):
                store.get_manifest("nope" + "x" * 60)
        finally:
            store.close()

    def test_iter_manifests(self, tmp_path: Path) -> None:
        store = CacheStore(tmp_path)
        try:
            store.put_manifest(_manifest("a" * 64))
            store.put_manifest(_manifest("b" * 64))
            keys = {m.cache_key for m in store.iter_manifests()}
            assert keys == {"a" * 64, "b" * 64}
        finally:
            store.close()


class TestContextManager:
    def test_context_closes(self, tmp_path: Path) -> None:
        store = CacheStore(tmp_path)
        with store:
            store.put_blob(b"x")
        # Should be usable again after reopening
        store2 = CacheStore(tmp_path)
        store2.close()
