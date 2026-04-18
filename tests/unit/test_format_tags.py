"""Unit tests for jellycell.format.tags."""

from __future__ import annotations

import pytest

from jellycell.format.cells import CellSpec
from jellycell.format.tags import TagParseError, parse_tags, render_tags


class TestParseTags:
    def test_empty_list_yields_default_step(self) -> None:
        assert parse_tags([]) == CellSpec(kind="step")

    def test_kind_parses(self) -> None:
        for kind, expected in [
            ("jc.load", "load"),
            ("jc.step", "step"),
            ("jc.figure", "figure"),
            ("jc.table", "table"),
            ("jc.setup", "setup"),
            ("jc.note", "note"),
        ]:
            spec = parse_tags([kind])
            assert spec.kind == expected

    def test_name_attr(self) -> None:
        assert parse_tags(["jc.step", "name=summary"]).name == "summary"

    def test_deps_attr(self) -> None:
        assert parse_tags(["jc.step", "deps=a,b,c"]).deps == ["a", "b", "c"]

    def test_deps_strips_whitespace(self) -> None:
        assert parse_tags(["jc.step", "deps=a, b , c"]).deps == ["a", "b", "c"]

    def test_empty_deps_yields_empty_list(self) -> None:
        assert parse_tags(["jc.step", "deps="]).deps == []

    def test_timeout_attr(self) -> None:
        assert parse_tags(["jc.step", "timeout=30"]).timeout_s == 30

    def test_unknown_jc_kind_raises(self) -> None:
        with pytest.raises(TagParseError, match="Unknown"):
            parse_tags(["jc.wibble"])

    def test_multiple_kinds_raises(self) -> None:
        with pytest.raises(TagParseError, match="Multiple"):
            parse_tags(["jc.load", "jc.step"])

    def test_bad_timeout_raises(self) -> None:
        with pytest.raises(TagParseError, match="timeout"):
            parse_tags(["jc.step", "timeout=fast"])

    def test_foreign_tags_ignored(self) -> None:
        spec = parse_tags(["papermill-parameters", "some-plugin-tag"])
        assert spec == CellSpec()

    def test_foreign_attr_tags_ignored(self) -> None:
        spec = parse_tags(["jc.step", "custom_attr=xyz"])
        assert spec == CellSpec(kind="step")


class TestRenderTags:
    def test_default_spec_yields_just_kind(self) -> None:
        assert render_tags(CellSpec()) == ["jc.step"]

    def test_full_spec_yields_canonical_list(self) -> None:
        spec = CellSpec(kind="step", name="s", deps=["a", "b"], timeout_s=30)
        # Multi-dep renders as multiple `deps=` tags (nbformat-safe).
        assert render_tags(spec) == ["jc.step", "name=s", "deps=a", "deps=b", "timeout=30"]

    def test_multiple_deps_tags_accumulate(self) -> None:
        spec = parse_tags(["jc.step", "deps=a", "deps=b", "deps=c"])
        assert spec.deps == ["a", "b", "c"]

    def test_semicolon_deps_separator(self) -> None:
        spec = parse_tags(["jc.step", "deps=a;b;c"])
        assert spec.deps == ["a", "b", "c"]

    def test_deps_deduped(self) -> None:
        spec = parse_tags(["jc.step", "deps=a", "deps=a;b"])
        assert spec.deps == ["a", "b"]

    def test_round_trip(self) -> None:
        for spec in [
            CellSpec(kind="load", name="raw"),
            CellSpec(kind="step", deps=["x", "y"]),
            CellSpec(kind="figure", name="hist", timeout_s=120),
        ]:
            assert parse_tags(render_tags(spec)) == spec
