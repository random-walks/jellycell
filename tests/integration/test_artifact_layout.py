"""[artifacts] layout setting drives jc.figure / jc.table default paths.

Explicit paths in ``jc.save(x, "artifacts/foo.json")`` are untouched — the
layout only applies when jellycell picks the location (path-less
``jc.figure()`` / ``jc.table(df)`` calls). Also covers the large-artifact
warning surfaced via ``RunReport.large_artifacts``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from jellycell.config import ArtifactsConfig, default_config
from jellycell.paths import Project
from jellycell.run import Runner

pytestmark = pytest.mark.integration


def _bootstrap(tmp_path: Path, *, layout: str = "flat", max_mb: int = 50) -> Project:
    cfg = default_config("layout-test")
    cfg.artifacts = ArtifactsConfig(layout=layout, max_committed_size_mb=max_mb)  # type: ignore[arg-type]
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "site", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    return Project(root=tmp_path.resolve(), config=cfg)


def _table_notebook(stem: str) -> str:
    """Notebook writing a table via jc.table() with no explicit path."""
    return (
        "# /// script\n"
        "# dependencies = []\n"
        "# ///\n"
        "\n"
        f'# %% tags=["jc.table", "name={stem}"]\n'
        "import pandas as pd\n"
        "import jellycell.api as jc\n"
        f'jc.table(pd.DataFrame({{"x": [1, 2]}}), name="{stem}")\n'
    )


@pytest.mark.skipif(
    pytest.importorskip("pandas", reason="pandas not installed") is None,
    reason="pandas required",
)
class TestLayoutFlat:
    def test_flat_writes_to_bare_artifacts_dir(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path, layout="flat")
        nb_path = project.notebooks_dir / "demo.py"
        nb_path.write_text(_table_notebook("summary"), encoding="utf-8")
        runner = Runner(project)
        try:
            report = runner.run(nb_path)
        finally:
            runner.close()
        assert report.status == "ok"
        assert (project.artifacts_dir / "summary.parquet").exists()


class TestLayoutByNotebook:
    def test_by_notebook_subfolders_artifacts_by_notebook_stem(self, tmp_path: Path) -> None:
        pytest.importorskip("pandas")
        project = _bootstrap(tmp_path, layout="by_notebook")
        nb_path = project.notebooks_dir / "alpha.py"
        nb_path.write_text(_table_notebook("summary"), encoding="utf-8")
        runner = Runner(project)
        try:
            report = runner.run(nb_path)
        finally:
            runner.close()
        assert report.status == "ok"
        assert (project.artifacts_dir / "alpha" / "summary.parquet").exists()
        # Flat location must NOT be written, or reviewers get a doubled tree.
        assert not (project.artifacts_dir / "summary.parquet").exists()


class TestLayoutByCell:
    def test_by_cell_nests_artifacts_under_notebook_and_cell(self, tmp_path: Path) -> None:
        pytest.importorskip("pandas")
        project = _bootstrap(tmp_path, layout="by_cell")
        nb_path = project.notebooks_dir / "beta.py"
        nb_path.write_text(_table_notebook("summary"), encoding="utf-8")
        runner = Runner(project)
        try:
            report = runner.run(nb_path)
        finally:
            runner.close()
        assert report.status == "ok"
        assert (project.artifacts_dir / "beta" / "summary" / "summary.parquet").exists()


class TestExplicitPathsWin:
    def test_explicit_jc_save_path_ignores_layout(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path, layout="by_cell")
        nb_path = project.notebooks_dir / "explicit.py"
        nb_path.write_text(
            "# /// script\n"
            "# dependencies = []\n"
            "# ///\n"
            "\n"
            '# %% tags=["jc.step", "name=save"]\n'
            "import jellycell.api as jc\n"
            'jc.save({"k": 1}, "artifacts/custom.json")\n',
            encoding="utf-8",
        )
        runner = Runner(project)
        try:
            report = runner.run(nb_path)
        finally:
            runner.close()
        assert report.status == "ok"
        # Explicit path → exactly that path, regardless of layout.
        assert (project.artifacts_dir / "custom.json").exists()
        assert not (project.artifacts_dir / "explicit" / "save" / "custom.json").exists()


class TestLargeArtifactWarning:
    def test_large_artifact_surfaces_in_report(self, tmp_path: Path) -> None:
        # Threshold 1 MB; write 1.5 MB so the warning fires without slowing the test.
        project = _bootstrap(tmp_path, max_mb=1)
        nb_path = project.notebooks_dir / "big.py"
        nb_path.write_text(
            "# /// script\n"
            "# dependencies = []\n"
            "# ///\n"
            "\n"
            '# %% tags=["jc.step", "name=dump"]\n'
            "from pathlib import Path\n"
            'p = Path("artifacts/dump.bin")\n'
            "p.parent.mkdir(parents=True, exist_ok=True)\n"
            'p.write_bytes(b"x" * (1_500_000))\n',
            encoding="utf-8",
        )
        runner = Runner(project)
        try:
            report = runner.run(nb_path)
        finally:
            runner.close()
        assert report.status == "ok"
        assert len(report.large_artifacts) == 1
        warning = report.large_artifacts[0]
        assert warning.path == "artifacts/dump.bin"
        assert warning.limit_mb == 1
        assert warning.size_mb > 1.0
        assert warning.cell_name == "dump"

    def test_threshold_zero_disables_warnings(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path, max_mb=0)
        nb_path = project.notebooks_dir / "big.py"
        nb_path.write_text(
            "# /// script\n"
            "# dependencies = []\n"
            "# ///\n"
            "\n"
            '# %% tags=["jc.step"]\n'
            "from pathlib import Path\n"
            'p = Path("artifacts/dump.bin")\n'
            "p.parent.mkdir(parents=True, exist_ok=True)\n"
            'p.write_bytes(b"x" * (5_000_000))\n',
            encoding="utf-8",
        )
        runner = Runner(project)
        try:
            report = runner.run(nb_path)
        finally:
            runner.close()
        assert report.large_artifacts == []
