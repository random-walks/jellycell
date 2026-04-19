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


class TestFigurePathOnly:
    """``jc.figure(path)`` with a pre-existing image file, no fig="""

    def _write_png(self, target: Path) -> None:
        # 1x1 transparent PNG — smallest valid payload, avoids a matplotlib dep.
        payload = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
            "89000000094944415478da63000100000500010d0a2db40000000049454e44ae"
            "426082"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)

    def test_returns_path_without_re_encoding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "artifacts" / "fig.png"
        self._write_png(src)
        before = src.read_bytes()

        out = jc.figure("artifacts/fig.png")

        assert out == src.resolve()
        # Path-only mode MUST NOT re-encode the image. Content unchanged.
        assert out.read_bytes() == before

    def test_passes_without_matplotlib_import(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Path-only mode must not pull in matplotlib (cheaper import graph).

        Simulates an environment where matplotlib isn't installed: a call
        that would have needed ``plt.gcf()`` still works if the path exists.
        """
        import sys

        # Sabotage matplotlib imports — if figure() reaches the render path,
        # the test fails with ImportError.
        monkeypatch.setitem(sys.modules, "matplotlib", None)
        monkeypatch.setitem(sys.modules, "matplotlib.pyplot", None)

        monkeypatch.chdir(tmp_path)
        src = tmp_path / "fig.png"
        self._write_png(src)

        out = jc.figure("fig.png")
        assert out.exists()

    def test_no_file_falls_back_to_matplotlib(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If ``path`` doesn't point to an existing file, old behavior wins."""
        monkeypatch.chdir(tmp_path)
        # No file at "nope.png" — should try to savefig via plt.gcf(). We
        # assert the ImportError surfaces (no matplotlib here) to confirm
        # we took the render branch, not the path-only branch.
        import sys

        monkeypatch.setitem(sys.modules, "matplotlib", None)
        monkeypatch.setitem(sys.modules, "matplotlib.pyplot", None)
        with pytest.raises((ImportError, AttributeError)):
            jc.figure("nope.png")
