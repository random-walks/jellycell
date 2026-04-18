"""Lock spec §10.1: every ``--json`` output has a stable schema.

Snapshots the JSON *structure* (top-level keys + field types) per command.
Field value changes don't trip the snapshot; adding/removing/renaming a
field does. Bumping requires a minor version bump + CHANGELOG entry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from jellycell.cli.app import app
from jellycell.config import default_config
from jellycell.paths import Project
from jellycell.run import Runner

pytestmark = pytest.mark.integration

runner = CliRunner()


def _project(tmp_path: Path) -> Project:
    cfg = default_config("schema-test")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "site", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    return Project(root=tmp_path.resolve(), config=cfg)


def _shape(data: Any, depth: int = 3) -> Any:
    """Reduce JSON data to a shape fingerprint — types, not values."""
    if depth <= 0:
        return type(data).__name__
    if isinstance(data, dict):
        return {k: _shape(v, depth - 1) for k, v in sorted(data.items())}
    if isinstance(data, list):
        if not data:
            return ["<empty>"]
        return [_shape(data[0], depth - 1)]
    if isinstance(data, bool):
        return "bool"
    if isinstance(data, int):
        return "int"
    if isinstance(data, float):
        return "float"
    if isinstance(data, str):
        return "str"
    if data is None:
        return "null"
    return type(data).__name__


def _snapshot(data_regression, cmd: list[str], basename: str) -> None:
    result = runner.invoke(app, cmd)
    assert result.exit_code in (0, 1), f"{cmd!r}: exit {result.exit_code}, out={result.stdout}"
    payload = json.loads(result.stdout)
    data_regression.check(_shape(payload), basename=basename)


class TestSchemas:
    def test_init(self, tmp_path: Path, data_regression: pytest.FixtureRequest) -> None:
        _snapshot(
            data_regression,
            ["--json", "init", str(tmp_path / "p"), "--name", "p"],
            basename="init",
        )

    def test_lint_clean(self, tmp_path: Path, data_regression: pytest.FixtureRequest) -> None:
        runner.invoke(app, ["init", str(tmp_path / "p"), "--name", "p"])
        _snapshot(
            data_regression,
            ["--json", "lint", str(tmp_path / "p")],
            basename="lint",
        )

    def test_new(self, tmp_path: Path, data_regression: pytest.FixtureRequest) -> None:
        runner.invoke(app, ["init", str(tmp_path / "p"), "--name", "p"])
        _snapshot(
            data_regression,
            ["--json", "new", "hello", "--project", str(tmp_path / "p")],
            basename="new",
        )

    def test_cache_list_empty(self, tmp_path: Path, data_regression: pytest.FixtureRequest) -> None:
        runner.invoke(app, ["init", str(tmp_path / "p"), "--name", "p"])
        _snapshot(
            data_regression,
            ["--json", "cache", "list", str(tmp_path / "p")],
            basename="cache_list",
        )

    def test_cache_rebuild_index(
        self, tmp_path: Path, data_regression: pytest.FixtureRequest
    ) -> None:
        runner.invoke(app, ["init", str(tmp_path / "p"), "--name", "p"])
        _snapshot(
            data_regression,
            ["--json", "cache", "rebuild-index", str(tmp_path / "p")],
            basename="cache_rebuild",
        )

    def test_cache_prune_dry_run(
        self, tmp_path: Path, data_regression: pytest.FixtureRequest
    ) -> None:
        runner.invoke(app, ["init", str(tmp_path / "p"), "--name", "p"])
        _snapshot(
            data_regression,
            ["--json", "cache", "prune", str(tmp_path / "p"), "--keep-last", "5", "--dry-run"],
            basename="cache_prune",
        )

    def test_run_report(self, tmp_path: Path, data_regression: pytest.FixtureRequest) -> None:
        project = _project(tmp_path)
        nb = project.notebooks_dir / "n.py"
        nb.write_text(
            "# /// script\n# dependencies = []\n# ///\n\n# %%\nx = 1\n",
            encoding="utf-8",
        )
        r = Runner(project)
        try:
            report = r.run(nb)
        finally:
            r.close()
        data_regression.check(_shape(report.model_dump()), basename="run_report")

    def test_render(self, tmp_path: Path, data_regression: pytest.FixtureRequest) -> None:
        project = _project(tmp_path)
        nb = project.notebooks_dir / "nb.py"
        nb.write_text(
            "# /// script\n# dependencies = []\n# ///\n\n# %%\nprint('hi')\n",
            encoding="utf-8",
        )
        r = Runner(project)
        try:
            r.run(nb)
        finally:
            r.close()
        _snapshot(
            data_regression,
            ["--json", "render", str(nb)],
            basename="render",
        )
