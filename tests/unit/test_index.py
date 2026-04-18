"""Unit tests for jellycell.cache.index."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from jellycell.cache.index import CacheIndex
from jellycell.cache.manifest import ArtifactRecord, Manifest
from jellycell.cache.store import CacheStore


def _manifest(cache_key: str, notebook: str = "n.py", with_artifact: bool = False) -> Manifest:
    artifacts = []
    if with_artifact:
        artifacts.append(
            ArtifactRecord(path="artifacts/x.parquet", sha256="a" * 64, size=100, mime="text/x")
        )
    return Manifest(
        cache_key=cache_key,
        notebook=notebook,
        cell_id=f"{notebook}:0",
        source_hash="s" * 64,
        env_hash="e" * 64,
        executed_at=datetime(2026, 4, 17, tzinfo=UTC),
        duration_ms=1,
        status="ok",
        artifacts=artifacts,
    )


class TestIndex:
    def test_insert_and_list_by_notebook(self, tmp_path: Path) -> None:
        with CacheIndex(tmp_path / "s.db") as idx:
            m = _manifest("k" * 64)
            idx.insert(m, tmp_path / "manifests" / f"{m.cache_key}.json")
            rows = idx.list_by_notebook("n.py")
            assert len(rows) == 1
            assert rows[0]["cache_key"] == m.cache_key

    def test_insert_replaces_existing(self, tmp_path: Path) -> None:
        with CacheIndex(tmp_path / "s.db") as idx:
            m1 = _manifest("k" * 64)
            m2 = _manifest("k" * 64)
            idx.insert(m1, tmp_path / "a.json")
            idx.insert(m2, tmp_path / "b.json")
            rows = idx.list_by_notebook("n.py")
            assert len(rows) == 1  # upsert, not duplicate

    def test_list_all_orders_by_executed_at_desc(self, tmp_path: Path) -> None:
        with CacheIndex(tmp_path / "s.db") as idx:
            m_old = Manifest(
                cache_key="a" * 64,
                notebook="a.py",
                cell_id="a:0",
                source_hash="s" * 64,
                env_hash="e" * 64,
                executed_at=datetime(2025, 1, 1, tzinfo=UTC),
                duration_ms=1,
                status="ok",
            )
            m_new = Manifest(
                cache_key="b" * 64,
                notebook="b.py",
                cell_id="b:0",
                source_hash="s" * 64,
                env_hash="e" * 64,
                executed_at=datetime(2026, 4, 17, tzinfo=UTC),
                duration_ms=1,
                status="ok",
            )
            idx.insert(m_old, tmp_path / "a.json")
            idx.insert(m_new, tmp_path / "b.json")
            rows = idx.list_all()
            assert rows[0]["cache_key"] == "b" * 64
            assert rows[1]["cache_key"] == "a" * 64

    def test_artifacts_tracked(self, tmp_path: Path) -> None:
        with CacheIndex(tmp_path / "s.db") as idx:
            m = _manifest("k" * 64, with_artifact=True)
            idx.insert(m, tmp_path / "x.json")
            # Query the artifacts table directly
            rows = idx._conn.execute(
                "SELECT sha256, path FROM artifacts WHERE producer_cache_key = ?",
                (m.cache_key,),
            ).fetchall()
            assert len(rows) == 1
            assert rows[0][0] == "a" * 64

    def test_rebuild_from_store(self, tmp_path: Path) -> None:
        store = CacheStore(tmp_path)
        idx = CacheIndex(tmp_path / "s.db")
        try:
            store.put_manifest(_manifest("a" * 64, notebook="x.py"))
            store.put_manifest(_manifest("b" * 64, notebook="x.py"))
            count = idx.rebuild_from_store(store)
            assert count == 2
            assert len(idx.list_by_notebook("x.py")) == 2
        finally:
            store.close()
            idx.close()

    def test_clear_empties_tables(self, tmp_path: Path) -> None:
        with CacheIndex(tmp_path / "s.db") as idx:
            idx.insert(_manifest("k" * 64), tmp_path / "x.json")
            idx.clear()
            assert idx.list_all() == []


class TestNotebookViewKey:
    """Regression tests for :meth:`CacheIndex.notebook_view_key`.

    The key is the server's response-cache key: it must change when
    either the notebook source bytes change OR the set of cell cache
    keys changes, and stay stable otherwise. Missing notebook files
    return ``None`` so the caller can skip caching and render the 404
    path naturally.
    """

    def test_stable_for_same_inputs(self, tmp_path: Path) -> None:
        (tmp_path / "notebooks").mkdir()
        nb = tmp_path / "notebooks" / "n.py"
        nb.write_text("# /// script\n# ///\nprint('hi')\n", encoding="utf-8")
        with CacheIndex(tmp_path / "state.db") as idx:
            k1 = idx.notebook_view_key(tmp_path, "notebooks/n.py")
            k2 = idx.notebook_view_key(tmp_path, "notebooks/n.py")
        assert k1 is not None
        assert k1 == k2

    def test_changes_on_source_edit(self, tmp_path: Path) -> None:
        (tmp_path / "notebooks").mkdir()
        nb = tmp_path / "notebooks" / "n.py"
        nb.write_text("# /// script\n# ///\nprint('hi')\n", encoding="utf-8")
        with CacheIndex(tmp_path / "state.db") as idx:
            before = idx.notebook_view_key(tmp_path, "notebooks/n.py")
            nb.write_text("# /// script\n# ///\nprint('different')\n", encoding="utf-8")
            after = idx.notebook_view_key(tmp_path, "notebooks/n.py")
        assert before != after

    def test_changes_on_new_manifest(self, tmp_path: Path) -> None:
        (tmp_path / "notebooks").mkdir()
        (tmp_path / "notebooks" / "n.py").write_text(
            "# /// script\n# ///\nprint('hi')\n", encoding="utf-8"
        )
        with CacheIndex(tmp_path / "state.db") as idx:
            empty_key = idx.notebook_view_key(tmp_path, "notebooks/n.py")
            # Indexing a cell for this notebook must rotate the key, even
            # though the source bytes haven't changed.
            idx.insert(_manifest("k" * 64, notebook="notebooks/n.py"), tmp_path / "x.json")
            populated_key = idx.notebook_view_key(tmp_path, "notebooks/n.py")
        assert empty_key != populated_key

    def test_none_for_missing_notebook(self, tmp_path: Path) -> None:
        with CacheIndex(tmp_path / "state.db") as idx:
            assert idx.notebook_view_key(tmp_path, "notebooks/gone.py") is None

    def test_isolated_between_notebooks(self, tmp_path: Path) -> None:
        """Adding a cell for notebook A doesn't affect notebook B's key."""
        (tmp_path / "notebooks").mkdir()
        nb_a = tmp_path / "notebooks" / "a.py"
        nb_b = tmp_path / "notebooks" / "b.py"
        nb_a.write_text("# /// script\n# ///\nx = 1\n", encoding="utf-8")
        nb_b.write_text("# /// script\n# ///\ny = 2\n", encoding="utf-8")
        with CacheIndex(tmp_path / "state.db") as idx:
            b_before = idx.notebook_view_key(tmp_path, "notebooks/b.py")
            idx.insert(_manifest("k" * 64, notebook="notebooks/a.py"), tmp_path / "x.json")
            b_after = idx.notebook_view_key(tmp_path, "notebooks/b.py")
        assert b_before == b_after
