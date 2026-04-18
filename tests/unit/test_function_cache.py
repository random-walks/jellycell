"""Unit tests for jellycell.cache.function_cache (jc.cache decorator)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from jellycell.api import cache as jc_cache
from jellycell.cache.function_cache import _FN_RETURN_INDEX, _function_cache_key
from jellycell.config import default_config
from jellycell.paths import Project
from jellycell.run.context import RunContext, reset_context, set_context


def _make_ctx(tmp_path: Path) -> RunContext:
    cfg = default_config("fn-cache")
    cfg.dump(tmp_path / "jellycell.toml")
    (tmp_path / ".jellycell" / "cache").mkdir(parents=True, exist_ok=True)
    project = Project(root=tmp_path.resolve(), config=cfg)
    return RunContext(
        notebook="notebooks/x.py",
        cell_id="x:0",
        cell_name=None,
        project=project,
    )


class TestStandalone:
    def test_passthrough_when_no_context(self) -> None:
        calls = 0

        @jc_cache
        def f(x: int) -> int:
            nonlocal calls
            calls += 1
            return x + 1

        assert f(3) == 4
        assert f(3) == 4
        # Without a RunContext, no caching.
        assert calls == 2


class TestInsideRun:
    def test_second_call_served_from_cache(self, tmp_path: Path) -> None:
        _FN_RETURN_INDEX.clear()
        ctx = _make_ctx(tmp_path)
        token = set_context(ctx)
        try:
            calls = 0

            @jc_cache
            def slow(x: int, *, y: int = 0) -> int:
                nonlocal calls
                calls += 1
                return x + y

            assert slow(1, y=2) == 3
            assert slow(1, y=2) == 3
            assert slow(1, y=2) == 3
            assert calls == 1
        finally:
            reset_context(token)

    def test_different_args_miss_each_other(self, tmp_path: Path) -> None:
        _FN_RETURN_INDEX.clear()
        ctx = _make_ctx(tmp_path)
        token = set_context(ctx)
        try:
            calls = 0

            @jc_cache
            def f(x: int) -> int:
                nonlocal calls
                calls += 1
                return x * 2

            assert f(1) == 2
            assert f(2) == 4
            assert calls == 2
        finally:
            reset_context(token)

    def test_unpicklable_args_raise_typeerror(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        token = set_context(ctx)
        try:

            @jc_cache
            def f(fn: Any) -> int:
                return 1

            with pytest.raises(TypeError, match="not pickleable"):
                f(lambda: 1)
        finally:
            reset_context(token)


class TestKeyDerivation:
    def test_same_inputs_same_key(self) -> None:
        def f(x: int) -> int:
            return x

        k1 = _function_cache_key(f, "def f(x): return x", (1,), {})
        k2 = _function_cache_key(f, "def f(x): return x", (1,), {})
        assert k1 == k2

    def test_different_args_different_key(self) -> None:
        def f(x: int) -> int:
            return x

        k1 = _function_cache_key(f, "def f(x): return x", (1,), {})
        k2 = _function_cache_key(f, "def f(x): return x", (2,), {})
        assert k1 != k2

    def test_source_change_changes_key(self) -> None:
        def f(x: int) -> int:
            return x

        k1 = _function_cache_key(f, "def f(x): return x", (1,), {})
        k2 = _function_cache_key(f, "def f(x): return x * 2", (1,), {})
        assert k1 != k2

    def test_kwargs_order_doesnt_matter(self) -> None:
        def f(**k: int) -> int:
            return sum(k.values())

        k1 = _function_cache_key(f, "", (), {"a": 1, "b": 2})
        k2 = _function_cache_key(f, "", (), {"b": 2, "a": 1})
        assert k1 == k2
