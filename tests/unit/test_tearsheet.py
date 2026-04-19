"""Unit tests for jellycell.export.tearsheet.

The tearsheet exporter is logic-only (no kernel, no runner) so these are
pure file-in/file-out tests. We construct :class:`Manifest` objects by
hand to exercise each branch: markdown narration, image inlining, JSON
summary flattening, setup-cell source surfacing, and artifact skipping.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from jellycell.cache.manifest import ArtifactRecord, Manifest
from jellycell.export import export_tearsheet


def _bootstrap_project(tmp_path: Path) -> Path:
    """Minimal ``<project>/{notebooks,artifacts,manuscripts}/`` layout."""
    for d in ("notebooks", "artifacts", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    return tmp_path


def _make_manifest(
    cell_id: str,
    *,
    artifacts: list[ArtifactRecord] | None = None,
    executed_at: datetime | None = None,
) -> Manifest:
    return Manifest(
        cache_key="k" * 64,
        notebook=f"notebooks/{cell_id.split(':', 1)[0]}.py",
        cell_id=cell_id,
        source_hash="s" * 64,
        env_hash="e" * 64,
        executed_at=executed_at or datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        duration_ms=5,
        status="ok",
        outputs=[],
        artifacts=artifacts or [],
    )


def _write_notebook(project: Path, body: str) -> Path:
    path = project / "notebooks" / "nb.py"
    path.write_text(body, encoding="utf-8")
    return path


class TestTitleExtraction:
    def test_uses_first_h1_from_markdown_cell(self, tmp_path: Path) -> None:
        project = _bootstrap_project(tmp_path)
        nb = _write_notebook(
            project,
            "# /// script\n# dependencies = []\n# ///\n\n"
            "# %% [markdown]\n# # Mortality study\n# intro paragraph\n",
        )
        out = export_tearsheet(
            nb,
            manifests_by_cell={},
            output_path=project / "manuscripts" / "nb.md",
            project_root=project,
        )
        text = out.read_text(encoding="utf-8")
        assert text.startswith("# Mortality study\n")
        # H1 line is stripped from the body so we don't duplicate the title.
        assert text.count("# Mortality study") == 1
        # Rest of the markdown cell survives.
        assert "intro paragraph" in text

    def test_falls_back_to_notebook_stem(self, tmp_path: Path) -> None:
        project = _bootstrap_project(tmp_path)
        nb = _write_notebook(project, "# /// script\n# dependencies = []\n# ///\n\nx = 1\n")
        out = export_tearsheet(
            nb,
            manifests_by_cell={},
            output_path=project / "manuscripts" / "nb.md",
            project_root=project,
        )
        assert out.read_text(encoding="utf-8").startswith("# Nb\n")


class TestSubtitle:
    def test_includes_source_link(self, tmp_path: Path) -> None:
        project = _bootstrap_project(tmp_path)
        nb = _write_notebook(
            project, "# /// script\n# dependencies = []\n# ///\n\n# %% [markdown]\n# # T\n"
        )
        out = export_tearsheet(
            nb,
            manifests_by_cell={},
            output_path=project / "manuscripts" / "nb.md",
            project_root=project,
        )
        text = out.read_text(encoding="utf-8")
        assert "[`notebooks/nb.py`](../notebooks/nb.py)" in text

    def test_timestamp_uses_latest_manifest(self, tmp_path: Path) -> None:
        project = _bootstrap_project(tmp_path)
        nb = _write_notebook(
            project, "# /// script\n# dependencies = []\n# ///\n\n# %% [markdown]\n# # T\n"
        )
        later = datetime(2026, 6, 1, 9, 0, 0, tzinfo=UTC)
        out = export_tearsheet(
            nb,
            manifests_by_cell={
                "nb:0": _make_manifest("nb:0"),
                "nb:1": _make_manifest("nb:1", executed_at=later),
            },
            output_path=project / "manuscripts" / "nb.md",
            project_root=project,
        )
        assert "2026-06-01" in out.read_text(encoding="utf-8")


class TestImageArtifacts:
    def test_inlines_png_with_relative_path(self, tmp_path: Path) -> None:
        project = _bootstrap_project(tmp_path)
        (project / "artifacts" / "plot.png").write_bytes(b"\x89PNG\r\n")
        nb = _write_notebook(
            project,
            "# /// script\n# dependencies = []\n# ///\n\n"
            "# %% [markdown]\n# # T\n\n"
            '# %% tags=["jc.figure", "name=raw_plot"]\n'
            "pass\n",
        )
        manifest = _make_manifest(
            "nb:1",
            artifacts=[
                ArtifactRecord(
                    path="artifacts/plot.png", sha256="a" * 64, size=12, mime="image/png"
                )
            ],
        )
        out = export_tearsheet(
            nb,
            manifests_by_cell={"nb:1": manifest},
            output_path=project / "manuscripts" / "nb.md",
            project_root=project,
        )
        text = out.read_text(encoding="utf-8")
        assert "![raw_plot](../artifacts/plot.png)" in text

    def test_skips_non_image_artifacts(self, tmp_path: Path) -> None:
        project = _bootstrap_project(tmp_path)
        nb = _write_notebook(
            project,
            "# /// script\n# dependencies = []\n# ///\n\n"
            "# %% [markdown]\n# # T\n\n"
            '# %% tags=["jc.step", "name=data"]\n'
            "pass\n",
        )
        manifest = _make_manifest(
            "nb:1",
            artifacts=[ArtifactRecord(path="artifacts/data.parquet", sha256="b" * 64, size=99)],
        )
        out = export_tearsheet(
            nb,
            manifests_by_cell={"nb:1": manifest},
            output_path=project / "manuscripts" / "nb.md",
            project_root=project,
        )
        assert ".parquet" not in out.read_text(encoding="utf-8")


class TestJsonArtifacts:
    def test_flattens_top_level_dict_into_table(self, tmp_path: Path) -> None:
        project = _bootstrap_project(tmp_path)
        (project / "artifacts" / "summary.json").write_text(
            json.dumps({"mean": 1.23, "count": 42}), encoding="utf-8"
        )
        nb = _write_notebook(
            project,
            "# /// script\n# dependencies = []\n# ///\n\n"
            "# %% [markdown]\n# # T\n\n"
            '# %% tags=["jc.step", "name=summary"]\n'
            "pass\n",
        )
        manifest = _make_manifest(
            "nb:1",
            artifacts=[
                ArtifactRecord(
                    path="artifacts/summary.json", sha256="c" * 64, size=42, mime="application/json"
                )
            ],
        )
        out = export_tearsheet(
            nb,
            manifests_by_cell={"nb:1": manifest},
            output_path=project / "manuscripts" / "nb.md",
            project_root=project,
        )
        text = out.read_text(encoding="utf-8")
        assert "**Summary**" in text
        assert "| field | value |" in text
        assert "| `mean` | `1.23` |" in text
        assert "| `count` | `42` |" in text

    def test_flattens_nested_keys_with_dots(self, tmp_path: Path) -> None:
        project = _bootstrap_project(tmp_path)
        (project / "artifacts" / "report.json").write_text(
            json.dumps({"residuals": {"mean": 0.0, "std": 1.0}, "alpha": 0.3}),
            encoding="utf-8",
        )
        nb = _write_notebook(
            project,
            "# /// script\n# dependencies = []\n# ///\n\n"
            "# %% [markdown]\n# # T\n\n"
            '# %% tags=["jc.step", "name=report"]\n'
            "pass\n",
        )
        manifest = _make_manifest(
            "nb:1",
            artifacts=[
                ArtifactRecord(
                    path="artifacts/report.json", sha256="d" * 64, size=9, mime="application/json"
                )
            ],
        )
        out = export_tearsheet(
            nb,
            manifests_by_cell={"nb:1": manifest},
            output_path=project / "manuscripts" / "nb.md",
            project_root=project,
        )
        text = out.read_text(encoding="utf-8")
        assert "`residuals.mean`" in text
        assert "`residuals.std`" in text
        assert "`alpha`" in text

    def test_multiple_jsons_from_one_cell_get_distinct_labels(self, tmp_path: Path) -> None:
        """One cell saving two JSONs gets two tables labeled by file stem, not cell name."""
        project = _bootstrap_project(tmp_path)
        (project / "artifacts" / "summary.json").write_text(json.dumps({"n": 4}), encoding="utf-8")
        (project / "artifacts" / "totals.json").write_text(
            json.dumps({"US": 765000}), encoding="utf-8"
        )
        nb = _write_notebook(
            project,
            "# /// script\n# dependencies = []\n# ///\n\n"
            "# %% [markdown]\n# # T\n\n"
            '# %% tags=["jc.step", "name=summary"]\n'
            "pass\n",
        )
        manifest = _make_manifest(
            "nb:1",
            artifacts=[
                ArtifactRecord(path="artifacts/summary.json", sha256="c" * 64, size=9),
                ArtifactRecord(path="artifacts/totals.json", sha256="d" * 64, size=15),
            ],
        )
        out = export_tearsheet(
            nb,
            manifests_by_cell={"nb:1": manifest},
            output_path=project / "manuscripts" / "nb.md",
            project_root=project,
        )
        text = out.read_text(encoding="utf-8")
        assert "**Summary**" in text
        assert "**Totals**" in text

    def test_skips_json_when_top_level_is_list(self, tmp_path: Path) -> None:
        project = _bootstrap_project(tmp_path)
        (project / "artifacts" / "items.json").write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        nb = _write_notebook(
            project,
            "# /// script\n# dependencies = []\n# ///\n\n"
            "# %% [markdown]\n# # T\n\n"
            '# %% tags=["jc.step", "name=items"]\n'
            "pass\n",
        )
        manifest = _make_manifest(
            "nb:1",
            artifacts=[ArtifactRecord(path="artifacts/items.json", sha256="e" * 64, size=7)],
        )
        out = export_tearsheet(
            nb,
            manifests_by_cell={"nb:1": manifest},
            output_path=project / "manuscripts" / "nb.md",
            project_root=project,
        )
        text = out.read_text(encoding="utf-8")
        assert "**Items**" not in text


class TestSetupCells:
    def test_setup_cell_source_shown(self, tmp_path: Path) -> None:
        project = _bootstrap_project(tmp_path)
        nb = _write_notebook(
            project,
            "# /// script\n# dependencies = []\n# ///\n\n"
            "# %% [markdown]\n# # T\n\n"
            '# %% tags=["jc.setup", "name=config"]\n'
            "EPOCHS = 5\nLR = 0.1\n",
        )
        out = export_tearsheet(
            nb,
            manifests_by_cell={"nb:1": _make_manifest("nb:1")},
            output_path=project / "manuscripts" / "nb.md",
            project_root=project,
        )
        text = out.read_text(encoding="utf-8")
        assert "**Config**" in text
        assert "EPOCHS = 5" in text
        assert "LR = 0.1" in text


class TestCodeCellSkip:
    def test_plain_step_cell_without_artifacts_is_omitted(self, tmp_path: Path) -> None:
        project = _bootstrap_project(tmp_path)
        nb = _write_notebook(
            project,
            "# /// script\n# dependencies = []\n# ///\n\n"
            "# %% [markdown]\n# # T\n\n"
            '# %% tags=["jc.step", "name=compute"]\n'
            "secret_internal_var = 42\n",
        )
        out = export_tearsheet(
            nb,
            manifests_by_cell={"nb:1": _make_manifest("nb:1")},
            output_path=project / "manuscripts" / "nb.md",
            project_root=project,
        )
        assert "secret_internal_var" not in out.read_text(encoding="utf-8")


class TestHeaderAndFooter:
    def test_header_labels_file_as_tearsheet(self, tmp_path: Path) -> None:
        project = _bootstrap_project(tmp_path)
        nb = _write_notebook(
            project, "# /// script\n# dependencies = []\n# ///\n\n# %% [markdown]\n# # T\n"
        )
        out = export_tearsheet(
            nb,
            manifests_by_cell={},
            output_path=project / "manuscripts" / "tearsheets" / "nb.md",
            project_root=project,
        )
        text = out.read_text(encoding="utf-8")
        # The word "Tearsheet" prefixes the source link so readers know what
        # they're looking at and where the content came from.
        assert "**Tearsheet**" in text
        assert "[`notebooks/nb.py`]" in text

    def test_header_links_html_report_when_present(self, tmp_path: Path) -> None:
        project = _bootstrap_project(tmp_path)
        (project / "site").mkdir(exist_ok=True)
        (project / "site" / "nb.html").write_text("<html></html>", encoding="utf-8")
        nb = _write_notebook(
            project, "# /// script\n# dependencies = []\n# ///\n\n# %% [markdown]\n# # T\n"
        )
        out = export_tearsheet(
            nb,
            manifests_by_cell={},
            output_path=project / "manuscripts" / "tearsheets" / "nb.md",
            project_root=project,
        )
        text = out.read_text(encoding="utf-8")
        assert "[HTML report]" in text
        assert "../../site/nb.html" in text

    def test_header_omits_html_link_when_absent(self, tmp_path: Path) -> None:
        project = _bootstrap_project(tmp_path)
        nb = _write_notebook(
            project, "# /// script\n# dependencies = []\n# ///\n\n# %% [markdown]\n# # T\n"
        )
        out = export_tearsheet(
            nb,
            manifests_by_cell={},
            output_path=project / "manuscripts" / "tearsheets" / "nb.md",
            project_root=project,
        )
        assert "HTML report" not in out.read_text(encoding="utf-8")

    def test_footer_warns_about_regeneration(self, tmp_path: Path) -> None:
        project = _bootstrap_project(tmp_path)
        nb = _write_notebook(
            project, "# /// script\n# dependencies = []\n# ///\n\n# %% [markdown]\n# # T\n"
        )
        out = export_tearsheet(
            nb,
            manifests_by_cell={},
            output_path=project / "manuscripts" / "tearsheets" / "nb.md",
            project_root=project,
        )
        text = out.read_text(encoding="utf-8")
        assert "Auto-generated" in text


class TestTearsheetTagFiltering:
    """Artifact filtering via the ``tearsheet`` tag (closes #15).

    When no cell/artifact carries the tag, behavior is unchanged (everything
    renderable inlines). When the tag appears anywhere in the notebook's
    artifacts or cell metadata, the exporter switches to opt-in mode and
    includes only artifacts tagged tearsheet (or produced by a tagged cell).
    """

    _NOTEBOOK_TWO_FIGS = (
        "# /// script\n# dependencies = []\n# ///\n\n"
        "# %% [markdown]\n# # Filtering\n\n"
        '# %% tags=["jc.figure", "name=main"]\n'
        "pass\n\n"
        '# %% tags=["jc.figure", "name=debug"]\n'
        "pass\n"
    )

    def _write_png(self, target: Path) -> None:
        # Same 1x1 transparent PNG fixture used elsewhere.
        payload = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
            "89000000094944415478da63000100000500010d0a2db40000000049454e44ae"
            "426082"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)

    def _bootstrap_two_figs(
        self, tmp_path: Path
    ) -> tuple[Path, Path, ArtifactRecord, ArtifactRecord]:
        project = _bootstrap_project(tmp_path)
        nb = _write_notebook(project, self._NOTEBOOK_TWO_FIGS)
        main = project / "artifacts" / "main.png"
        debug = project / "artifacts" / "debug.png"
        self._write_png(main)
        self._write_png(debug)
        main_art = ArtifactRecord(
            path="artifacts/main.png", sha256="a" * 64, size=main.stat().st_size
        )
        debug_art = ArtifactRecord(
            path="artifacts/debug.png", sha256="b" * 64, size=debug.stat().st_size
        )
        return project, nb, main_art, debug_art

    def test_no_tags_anywhere_means_include_all(self, tmp_path: Path) -> None:
        """Regression: legacy notebooks still include every renderable artifact."""
        project, nb, main_art, debug_art = self._bootstrap_two_figs(tmp_path)
        manifests = {
            "nb:1": _make_manifest("nb:1", artifacts=[main_art]),
            "nb:2": _make_manifest("nb:2", artifacts=[debug_art]),
        }
        out = export_tearsheet(
            nb,
            manifests_by_cell=manifests,
            output_path=project / "manuscripts" / "tearsheets" / "nb.md",
            project_root=project,
        )
        text = out.read_text(encoding="utf-8")
        assert "main.png" in text
        assert "debug.png" in text

    def test_artifact_level_tag_filters(self, tmp_path: Path) -> None:
        """``jc.figure(tags=['tearsheet'])`` on one artifact excludes the untagged one."""
        project, nb, main_art, debug_art = self._bootstrap_two_figs(tmp_path)
        main_art.tags = ["tearsheet"]
        manifests = {
            "nb:1": _make_manifest("nb:1", artifacts=[main_art]),
            "nb:2": _make_manifest("nb:2", artifacts=[debug_art]),
        }
        out = export_tearsheet(
            nb,
            manifests_by_cell=manifests,
            output_path=project / "manuscripts" / "tearsheets" / "nb.md",
            project_root=project,
        )
        text = out.read_text(encoding="utf-8")
        assert "main.png" in text
        # Debug figure excluded — untagged artifact under opt-in mode.
        assert "debug.png" not in text

    def test_cell_level_tag_filters(self, tmp_path: Path) -> None:
        """Cell-level ``tearsheet`` tag marks every artifact from that cell."""
        project = _bootstrap_project(tmp_path)
        nb = _write_notebook(
            project,
            "# /// script\n# dependencies = []\n# ///\n\n"
            "# %% [markdown]\n# # Filtering\n\n"
            '# %% tags=["jc.figure", "name=main", "tearsheet"]\n'
            "pass\n\n"
            '# %% tags=["jc.figure", "name=debug"]\n'
            "pass\n",
        )
        main = project / "artifacts" / "main.png"
        debug = project / "artifacts" / "debug.png"
        self._write_png(main)
        self._write_png(debug)
        main_art = ArtifactRecord(
            path="artifacts/main.png", sha256="a" * 64, size=main.stat().st_size
        )
        debug_art = ArtifactRecord(
            path="artifacts/debug.png", sha256="b" * 64, size=debug.stat().st_size
        )
        manifests = {
            "nb:1": _make_manifest("nb:1", artifacts=[main_art]),
            "nb:2": _make_manifest("nb:2", artifacts=[debug_art]),
        }
        out = export_tearsheet(
            nb,
            manifests_by_cell=manifests,
            output_path=project / "manuscripts" / "tearsheets" / "nb.md",
            project_root=project,
        )
        text = out.read_text(encoding="utf-8")
        assert "main.png" in text
        # Filter engaged because cell 1 has the tag; debug cell (no tag) excluded.
        assert "debug.png" not in text

    def test_json_artifacts_respect_filter(self, tmp_path: Path) -> None:
        """Filtering works identically for JSON summaries, not just images."""
        project = _bootstrap_project(tmp_path)
        nb = _write_notebook(
            project,
            "# /// script\n# dependencies = []\n# ///\n\n"
            '# %% tags=["jc.step", "name=report"]\n'
            "pass\n\n"
            '# %% tags=["jc.step", "name=diagnostic"]\n'
            "pass\n",
        )
        (project / "artifacts").mkdir(exist_ok=True)
        (project / "artifacts" / "headline.json").write_text(
            json.dumps({"value": 42}), encoding="utf-8"
        )
        (project / "artifacts" / "scratch.json").write_text(
            json.dumps({"debug": True}), encoding="utf-8"
        )
        headline = ArtifactRecord(
            path="artifacts/headline.json",
            sha256="a" * 64,
            size=10,
            tags=["tearsheet"],
        )
        scratch = ArtifactRecord(
            path="artifacts/scratch.json", sha256="b" * 64, size=10
        )
        manifests = {
            "nb:0": _make_manifest("nb:0", artifacts=[headline]),
            "nb:1": _make_manifest("nb:1", artifacts=[scratch]),
        }
        out = export_tearsheet(
            nb,
            manifests_by_cell=manifests,
            output_path=project / "manuscripts" / "tearsheets" / "nb.md",
            project_root=project,
        )
        text = out.read_text(encoding="utf-8")
        # Headline JSON is flattened into a table.
        assert "`value`" in text
        # Debug JSON not rendered at all.
        assert "`debug`" not in text
        assert "Regenerating overwrites this file" in text
