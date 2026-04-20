"""Unit tests for :mod:`jellycell.tearsheets` — the Python API for manuscript output.

Mirrors the three public helpers one-for-one:

- :func:`jellycell.tearsheets.findings` — results dict → FINDINGS.md
- :func:`jellycell.tearsheets.methodology` — section spec → METHODOLOGY.md
- :func:`jellycell.tearsheets.audit` — notebook → per-notebook tearsheet

``audit`` is a thin wrapper over the existing CLI exporter; tests here
verify the plumbing (project discovery, manifest lookup, output write)
and leave the rendering details to the existing
``tests/integration/test_export_tearsheet.py`` suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from jellycell import tearsheets as jt
from jellycell._version import __version__
from jellycell.paths import ProjectNotFoundError


class TestFindings:
    def test_writes_file_and_returns_path(self, tmp_path: Path) -> None:
        out = tmp_path / "FINDINGS.md"
        result = jt.findings(
            results={"twfe": {"att": 0.2, "n_obs": 1234}},
            out_path=out,
            project="showcase",
        )
        assert result == out
        assert out.exists()

    def test_header_carries_project_and_version(self, tmp_path: Path) -> None:
        out = tmp_path / "FINDINGS.md"
        jt.findings(
            results={"twfe": {"att": 0.2}},
            out_path=out,
            project="rat-containerization",
        )
        text = out.read_text(encoding="utf-8")
        assert "# Findings" in text
        assert "rat-containerization" in text
        # Default version pinned to current jellycell version.
        assert f"jellycell {__version__}" in text

    def test_template_overrides_pin_author_and_date(self, tmp_path: Path) -> None:
        out = tmp_path / "FINDINGS.md"
        jt.findings(
            results={"twfe": {"att": 0.2}},
            out_path=out,
            project="showcase",
            template_overrides={
                "author": "Blaise",
                "author_url": "https://ubik.studio",
                "month_year": "April 2026",
                "version": "1.4.0",
            },
        )
        text = out.read_text(encoding="utf-8")
        # Author rendered as markdown link when both name + URL are pinned.
        assert "[Blaise](https://ubik.studio)" in text
        assert "April 2026" in text
        assert "jellycell 1.4.0" in text

    def test_each_estimator_becomes_h2_with_table(self, tmp_path: Path) -> None:
        out = tmp_path / "FINDINGS.md"
        jt.findings(
            results={
                "twfe": {"att": 0.2, "n_obs": 1234},
                "cs": {"att": 0.25, "n_obs": 1180},
            },
            out_path=out,
            project="p",
        )
        text = out.read_text(encoding="utf-8")
        assert "## twfe" in text
        assert "## cs" in text
        # Two-column tables with key/value.
        assert "| Metric | Value |" in text
        assert "| `att` | `0.2` |" in text
        assert "| `n_obs` | `1234` |" in text
        assert "| `n_obs` | `1180` |" in text

    def test_nested_dict_flattens_to_dotted_keys(self, tmp_path: Path) -> None:
        out = tmp_path / "FINDINGS.md"
        jt.findings(
            results={"cs": {"att": {"estimate": 0.2, "se": 0.05}, "n": 1234}},
            out_path=out,
            project="p",
        )
        text = out.read_text(encoding="utf-8")
        assert "| `att.estimate` | `0.2` |" in text
        assert "| `att.se` | `0.05` |" in text
        assert "| `n` | `1234` |" in text

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        out = tmp_path / "manuscripts" / "deep" / "FINDINGS.md"
        jt.findings(
            results={"twfe": {"att": 0.2}},
            out_path=out,
            project="p",
        )
        assert out.exists()

    def test_empty_results_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="results is empty"):
            jt.findings(
                results={},
                out_path=tmp_path / "FINDINGS.md",
                project="p",
            )

    def test_byte_stable_regeneration_with_pinned_fields(self, tmp_path: Path) -> None:
        """Two calls with the same inputs + pinned month_year produce byte-identical output."""
        pinned = {
            "author": "Blaise",
            "month_year": "April 2026",
            "version": "1.4.0",
        }
        out_a = tmp_path / "A.md"
        out_b = tmp_path / "B.md"
        results = {"twfe": {"att": 0.2, "n_obs": 1234}}
        jt.findings(results=results, out_path=out_a, project="p", template_overrides=pinned)
        jt.findings(results=results, out_path=out_b, project="p", template_overrides=pinned)
        assert out_a.read_bytes() == out_b.read_bytes()


class TestMethodology:
    def test_writes_file_and_returns_path(self, tmp_path: Path) -> None:
        out = tmp_path / "METHODOLOGY.md"
        result = jt.methodology(
            spec={"Data source": "Weekly transit ridership panel, 2019-2024."},
            out_path=out,
            project="showcase",
        )
        assert result == out
        assert out.exists()

    def test_sections_become_h2_headings(self, tmp_path: Path) -> None:
        out = tmp_path / "METHODOLOGY.md"
        jt.methodology(
            spec={
                "Data source": "Panel of 132 stations over 60 weeks.",
                "Identification": "TWFE + CS robustness checks.",
            },
            out_path=out,
            project="p",
        )
        text = out.read_text(encoding="utf-8")
        assert "## Data source" in text
        assert "## Identification" in text
        # Bodies present verbatim.
        assert "Panel of 132 stations over 60 weeks." in text
        assert "TWFE + CS robustness checks." in text

    def test_preserves_markdown_in_body(self, tmp_path: Path) -> None:
        out = tmp_path / "METHODOLOGY.md"
        jt.methodology(
            spec={
                "Setup": "**Key insight**: this is *markdown*.\n\n- bullet\n- bullet\n\n"
                "```python\nprint('hi')\n```"
            },
            out_path=out,
            project="p",
        )
        text = out.read_text(encoding="utf-8")
        assert "**Key insight**" in text
        assert "*markdown*" in text
        assert "- bullet" in text
        assert "```python" in text

    def test_empty_body_renders_placeholder(self, tmp_path: Path) -> None:
        out = tmp_path / "METHODOLOGY.md"
        jt.methodology(
            spec={"Stub section": ""},
            out_path=out,
            project="p",
        )
        text = out.read_text(encoding="utf-8")
        assert "*(section left blank)*" in text

    def test_empty_spec_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="spec is empty"):
            jt.methodology(
                spec={},
                out_path=tmp_path / "M.md",
                project="p",
            )

    def test_ordering_preserved(self, tmp_path: Path) -> None:
        """Python dicts preserve insertion order — callers can rely on that."""
        out = tmp_path / "M.md"
        jt.methodology(
            spec={"Z-last": "late", "A-first": "early", "M-middle": "middle"},
            out_path=out,
            project="p",
        )
        text = out.read_text(encoding="utf-8")
        z_pos = text.index("Z-last")
        a_pos = text.index("A-first")
        m_pos = text.index("M-middle")
        assert z_pos < a_pos < m_pos


class TestAudit:
    def test_raises_when_notebook_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="notebook not found"):
            jt.audit(
                tmp_path / "does_not_exist.py",
                out_path=tmp_path / "AUDIT.md",
            )

    def test_raises_when_no_jellycell_toml(self, tmp_path: Path) -> None:
        nb = tmp_path / "orphan.py"
        nb.write_text(
            "# /// script\n# dependencies = []\n# ///\n\n# %% [markdown]\n# # Orphan\n",
            encoding="utf-8",
        )
        with pytest.raises(ProjectNotFoundError):
            jt.audit(nb, out_path=tmp_path / "AUDIT.md")

    def test_writes_audit_for_scaffolded_project(self, tmp_path: Path) -> None:
        """End-to-end: init a project, audit its starter notebook, get a file."""
        from jellycell.config import default_config

        cfg = default_config("audit-test")
        cfg.dump(tmp_path / "jellycell.toml")
        for d in ("notebooks", "data", "artifacts", "site", "manuscripts"):
            (tmp_path / d).mkdir(exist_ok=True)
        nb = tmp_path / "notebooks" / "tour.py"
        nb.write_text(
            "# /// script\n# dependencies = []\n# ///\n\n"
            "# %% [markdown]\n# # Tour\n\n"
            '# %% tags=["jc.step", "name=hello"]\n'
            "print('hi')\n",
            encoding="utf-8",
        )

        out = tmp_path / "manuscripts" / "tearsheets" / "tour.md"
        result = jt.audit(nb, out_path=out)
        assert result == out
        assert out.exists()
        text = out.read_text(encoding="utf-8")
        # Tearsheet exporter header keeps "**Tearsheet**".
        assert "**Tearsheet**" in text
        # The markdown cell survives into the output.
        assert "# Tour" in text or "Tour" in text
