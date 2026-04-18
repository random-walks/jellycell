"""Integration tests for the Starlette server routes (no uvicorn)."""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from jellycell.config import default_config
from jellycell.paths import Project
from jellycell.run import Runner
from jellycell.server import build_app

pytestmark = pytest.mark.integration


def _project(tmp_path: Path) -> Project:
    cfg = default_config("server-test")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "site", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    return Project(root=tmp_path.resolve(), config=cfg)


SAMPLE = (
    '# /// script\n# dependencies = []\n# ///\n\n# %% tags=["jc.step", "name=hi"]\nprint("hello")\n'
)


def _bootstrap_with_run(tmp_path: Path) -> Project:
    project = _project(tmp_path)
    nb_path = project.notebooks_dir / "sample.py"
    nb_path.write_text(SAMPLE, encoding="utf-8")
    runner = Runner(project)
    try:
        runner.run(nb_path)
    finally:
        runner.close()
    return project


def test_index_route_returns_html(tmp_path: Path) -> None:
    project = _bootstrap_with_run(tmp_path)
    app = build_app(project)
    with TestClient(app) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "sample" in resp.text


def test_notebook_route_returns_html(tmp_path: Path) -> None:
    project = _bootstrap_with_run(tmp_path)
    app = build_app(project)
    with TestClient(app) as client:
        resp = client.get("/nb/sample")
        assert resp.status_code == 200
        assert "sample" in resp.text
        assert "hello" in resp.text


def test_notebook_route_404(tmp_path: Path) -> None:
    project = _bootstrap_with_run(tmp_path)
    app = build_app(project)
    with TestClient(app) as client:
        resp = client.get("/nb/nonexistent")
        assert resp.status_code == 404


def test_state_json(tmp_path: Path) -> None:
    project = _bootstrap_with_run(tmp_path)
    app = build_app(project)
    with TestClient(app) as client:
        resp = client.get("/api/state.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["schema_version"] == 1
        assert data["project"] == "server-test"


def test_artifacts_are_served(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project.artifacts_dir / "note.txt").write_text("jellycell", encoding="utf-8")
    app = build_app(project)
    with TestClient(app) as client:
        resp = client.get("/artifacts/note.txt")
        assert resp.status_code == 200
        assert resp.text == "jellycell"
