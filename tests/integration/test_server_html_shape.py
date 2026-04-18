"""Server HTML-shape smoke tests.

Verify the user-visible pieces of the live-view server, not just status codes.
Complements ``test_server_routes.py`` and guards against regressions in the
template / renderer / routing layers.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from jellycell.config import default_config
from jellycell.paths import Project
from jellycell.run import Runner
from jellycell.server import build_app

pytestmark = pytest.mark.integration


SAMPLE_NOTEBOOK = (
    "# /// script\n"
    "# dependencies = []\n"
    "# ///\n"
    "\n"
    "# %% [markdown]\n"
    "# # Sample notebook\n"
    "\n"
    '# %% tags=["jc.step", "name=hi"]\n'
    "x = 1 + 1\n"
    "print('hello from smoke')\n"
)


def _bootstrapped_project(tmp_path: Path) -> Project:
    cfg = default_config("smoke")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "reports", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    project = Project(root=tmp_path.resolve(), config=cfg)
    nb = project.notebooks_dir / "sample.py"
    nb.write_text(SAMPLE_NOTEBOOK, encoding="utf-8")
    runner = Runner(project)
    try:
        runner.run(nb)
    finally:
        runner.close()
    return project


class TestIndexShape:
    def test_index_has_project_title(self, tmp_path: Path) -> None:
        project = _bootstrapped_project(tmp_path)
        with TestClient(build_app(project)) as client:
            resp = client.get("/")
            assert resp.status_code == 200
            assert "smoke" in resp.text

    def test_index_has_notebook_link(self, tmp_path: Path) -> None:
        project = _bootstrapped_project(tmp_path)
        with TestClient(build_app(project)) as client:
            resp = client.get("/")
            # The rendered index uses relative <stem>.html links so static
            # and served modes share markup.
            assert 'href="sample.html"' in resp.text

    def test_index_link_resolves_on_server(self, tmp_path: Path) -> None:
        """Clicking the .html link from the index must resolve on the server."""
        project = _bootstrapped_project(tmp_path)
        with TestClient(build_app(project)) as client:
            resp = client.get("/sample.html")
            assert resp.status_code == 200, resp.text
            assert "Sample notebook" in resp.text

    def test_index_shows_recent_runs_table(self, tmp_path: Path) -> None:
        project = _bootstrapped_project(tmp_path)
        with TestClient(build_app(project)) as client:
            resp = client.get("/")
            assert "Recent runs" in resp.text
            assert "sample:1" in resp.text


class TestNotebookShape:
    def test_notebook_page_has_cells(self, tmp_path: Path) -> None:
        project = _bootstrapped_project(tmp_path)
        with TestClient(build_app(project)) as client:
            resp = client.get("/nb/sample")
            assert resp.status_code == 200
            # One jc-cell element per cell; confirm at least markdown + code.
            cells = re.findall(r'class="jc-cell jc-cell-(\w+)"', resp.text)
            assert "markdown" in cells
            assert "code" in cells

    def test_notebook_page_has_toggle_buttons(self, tmp_path: Path) -> None:
        project = _bootstrapped_project(tmp_path)
        with TestClient(build_app(project)) as client:
            resp = client.get("/nb/sample")
            assert 'class="jc-toggle"' in resp.text
            # Each toggle has aria-expanded=true by default
            assert 'aria-expanded="true"' in resp.text

    def test_notebook_page_has_pygments_highlighting(self, tmp_path: Path) -> None:
        project = _bootstrapped_project(tmp_path)
        with TestClient(build_app(project)) as client:
            resp = client.get("/nb/sample")
            # Pygments wraps code in a div with the configured cssclass.
            # Token spans use the "friendly" style's class names (one- or
            # two-letter abbreviations).
            assert 'class="jc-code"' in resp.text
            assert "<span class=" in resp.text

    def test_notebook_page_has_output_block(self, tmp_path: Path) -> None:
        project = _bootstrapped_project(tmp_path)
        with TestClient(build_app(project)) as client:
            resp = client.get("/nb/sample")
            # Stream output rendered as a <pre>
            assert "jc-stream" in resp.text
            assert "hello from smoke" in resp.text

    def test_notebook_page_has_sse_client_hook(self, tmp_path: Path) -> None:
        project = _bootstrapped_project(tmp_path)
        with TestClient(build_app(project)) as client:
            resp = client.get("/nb/sample")
            # Script references /events for live reload
            assert "/events" in resp.text

    def test_notebook_page_has_breadcrumb_to_index(self, tmp_path: Path) -> None:
        project = _bootstrapped_project(tmp_path)
        with TestClient(build_app(project)) as client:
            resp = client.get("/nb/sample")
            assert 'href="index.html"' in resp.text

    def test_breadcrumb_index_link_resolves(self, tmp_path: Path) -> None:
        """The `/index.html` route matches the rendered breadcrumb."""
        project = _bootstrapped_project(tmp_path)
        with TestClient(build_app(project)) as client:
            assert client.get("/index.html").status_code == 200

    def test_notebook_page_has_cell_toc(self, tmp_path: Path) -> None:
        project = _bootstrapped_project(tmp_path)
        with TestClient(build_app(project)) as client:
            resp = client.get("/nb/sample")
            assert 'class="jc-toc' in resp.text
            assert 'href="#cell-' in resp.text
            assert "hi</a>" in resp.text  # named code cell surfaces in TOC

    def test_notebook_page_has_deep_link_anchors(self, tmp_path: Path) -> None:
        project = _bootstrapped_project(tmp_path)
        with TestClient(build_app(project)) as client:
            resp = client.get("/nb/sample")
            assert 'class="jc-cell-ordinal" href="#cell-' in resp.text


class TestArtifactsInNotebook:
    """Cells that wrote files via ``jc.save`` get artifact chips on the page."""

    NB_WITH_ARTIFACT = (
        "# /// script\n"
        "# dependencies = []\n"
        "# ///\n"
        "\n"
        '# %% tags=["jc.step", "name=persist"]\n'
        "import jellycell.api as jc\n"
        "jc.save({'x': 1}, 'artifacts/smoke.json')\n"
    )

    def _project_with_artifact(self, tmp_path: Path) -> Project:
        cfg = default_config("smoke")
        cfg.dump(tmp_path / "jellycell.toml")
        for d in ("notebooks", "data", "artifacts", "reports", "manuscripts"):
            (tmp_path / d).mkdir(exist_ok=True)
        project = Project(root=tmp_path.resolve(), config=cfg)
        nb = project.notebooks_dir / "hasart.py"
        nb.write_text(self.NB_WITH_ARTIFACT, encoding="utf-8")
        runner = Runner(project)
        try:
            runner.run(nb)
        finally:
            runner.close()
        return project

    def test_artifact_chip_appears_under_producing_cell(self, tmp_path: Path) -> None:
        project = self._project_with_artifact(tmp_path)
        with TestClient(build_app(project)) as client:
            resp = client.get("/nb/hasart")
            assert "jc-artifact-chip" in resp.text
            assert "smoke.json" in resp.text

    def test_artifact_chip_href_resolves_via_artifacts_mount(self, tmp_path: Path) -> None:
        project = self._project_with_artifact(tmp_path)
        with TestClient(build_app(project)) as client:
            resp = client.get("/artifacts/smoke.json")
            assert resp.status_code == 200
            assert '"x"' in resp.text


class TestPrevNextNav:
    """Multi-notebook projects get prev/next + sidebar listing."""

    def _project_with_many(self, tmp_path: Path, names: list[str]) -> Project:
        cfg = default_config("multi")
        cfg.dump(tmp_path / "jellycell.toml")
        for d in ("notebooks", "data", "artifacts", "reports", "manuscripts"):
            (tmp_path / d).mkdir(exist_ok=True)
        project = Project(root=tmp_path.resolve(), config=cfg)
        body = '# /// script\n# dependencies = []\n# ///\n\n# %%\nprint("hi")\n'
        for name in names:
            (project.notebooks_dir / name).write_text(body, encoding="utf-8")
        runner = Runner(project)
        try:
            for name in names:
                runner.run(project.notebooks_dir / name)
        finally:
            runner.close()
        return project

    def test_middle_notebook_has_both_prev_and_next(self, tmp_path: Path) -> None:
        project = self._project_with_many(tmp_path, ["a.py", "b.py", "c.py"])
        with TestClient(build_app(project)) as client:
            resp = client.get("/nb/b")
            assert 'href="a.html"' in resp.text
            assert 'href="c.html"' in resp.text

    def test_notebook_list_in_sidebar_marks_current(self, tmp_path: Path) -> None:
        project = self._project_with_many(tmp_path, ["a.py", "b.py"])
        with TestClient(build_app(project)) as client:
            resp = client.get("/nb/a")
            assert 'aria-current="page"' in resp.text


class TestApiStateShape:
    def test_state_json_has_contract_fields(self, tmp_path: Path) -> None:
        project = _bootstrapped_project(tmp_path)
        with TestClient(build_app(project)) as client:
            data = client.get("/api/state.json").json()
            assert data["schema_version"] == 1
            assert data["project"] == "smoke"
            assert "recent_runs" in data
            assert isinstance(data["recent_runs"], list)
            assert len(data["recent_runs"]) >= 1
