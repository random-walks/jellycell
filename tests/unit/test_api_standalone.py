"""Unit tests for jellycell.api in standalone (no RunContext) mode."""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import pytest

from jellycell import api as jc
from jellycell.run.context import get_context


class TestStandaloneSave:
    def test_save_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        out = jc.save({"x": 1}, "out.json")
        assert out.exists()
        data = json.loads(out.read_text())
        assert data == {"x": 1}

    def test_save_pickle(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        out = jc.save([1, 2, 3], "out.pkl")
        assert pickle.loads(out.read_bytes()) == [1, 2, 3]

    def test_save_creates_parent_dirs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        out = jc.save({"a": 1}, "subdir/out.json")
        assert out.exists()

    def test_unsupported_format_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ValueError, match="Unsupported format"):
            jc.save({"x": 1}, "out.xyz")


class TestStandaloneLoad:
    def test_load_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "in.json").write_text(json.dumps({"x": 42}))
        assert jc.load("in.json") == {"x": 42}

    def test_load_pickle(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "in.pkl").write_bytes(pickle.dumps("hello"))
        assert jc.load("in.pkl") == "hello"


class TestCtx:
    def test_inside_run_is_false_standalone(self) -> None:
        assert jc.ctx.inside_run is False

    def test_notebook_is_none_standalone(self) -> None:
        assert jc.ctx.notebook is None

    def test_cell_id_is_none_standalone(self) -> None:
        assert jc.ctx.cell_id is None


class TestDeps:
    def test_deps_is_noop_standalone(self) -> None:
        # Doesn't raise, doesn't do anything observable when standalone.
        jc.deps("a", "b", "c")
        assert get_context() is None


class TestCacheDecorator:
    def test_identity_in_phase_2(self) -> None:
        @jc.cache
        def f(x: int) -> int:
            return x + 1

        assert f(1) == 2
