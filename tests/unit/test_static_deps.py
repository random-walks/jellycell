"""Unit tests for jellycell.format.static_deps."""

from __future__ import annotations

from jellycell.format.static_deps import extract_loaded_paths, extract_static_deps


class TestExtractStaticDeps:
    def test_jc_deps_simple(self) -> None:
        src = 'import jellycell.api as jc\njc.deps("raw", "env")\nx = 1\n'
        assert extract_static_deps(src) == ["raw", "env"]

    def test_fully_qualified(self) -> None:
        src = 'import jellycell\njellycell.api.deps("a", "b")\n'
        assert extract_static_deps(src) == ["a", "b"]

    def test_dedupes(self) -> None:
        src = 'import jellycell.api as jc\njc.deps("a")\njc.deps("a", "b")\n'
        assert extract_static_deps(src) == ["a", "b"]

    def test_skips_non_literal_args(self) -> None:
        src = 'import jellycell.api as jc\nname = "a"\njc.deps(name)\n'
        assert extract_static_deps(src) == []

    def test_empty_when_no_jc_deps_call(self) -> None:
        assert extract_static_deps("x = 1\n") == []

    def test_syntax_error_returns_empty(self) -> None:
        assert extract_static_deps("def f(:\n") == []

    def test_ignores_other_jc_calls(self) -> None:
        src = 'import jellycell.api as jc\njc.save({}, "x.json")\n'
        assert extract_static_deps(src) == []


class TestExtractLoadedPaths:
    def test_simple_load(self) -> None:
        src = 'import jellycell.api as jc\nx = jc.load("artifacts/summary.json")\n'
        assert extract_loaded_paths(src) == ["artifacts/summary.json"]

    def test_multiple_loads(self) -> None:
        src = (
            "import jellycell.api as jc\n"
            'a = jc.load("artifacts/a.parquet")\n'
            'b = jc.load("artifacts/b.parquet")\n'
        )
        assert extract_loaded_paths(src) == ["artifacts/a.parquet", "artifacts/b.parquet"]

    def test_skips_non_literal(self) -> None:
        src = 'import jellycell.api as jc\np = "x"\nx = jc.load(p)\n'
        assert extract_loaded_paths(src) == []

    def test_empty_when_no_load(self) -> None:
        assert extract_loaded_paths("x = 1\n") == []
