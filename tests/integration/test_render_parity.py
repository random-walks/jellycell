"""Static render and server render must produce the same HTML.

The two code paths (``jellycell render`` static + ``jellycell view`` live)
share the :class:`Renderer` but are invoked separately. This test guards
against silent drift — a change that touches one path should trip this.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from jellycell.config import default_config
from jellycell.paths import Project
from jellycell.render import Renderer
from jellycell.run import Runner
from jellycell.server import build_app

pytestmark = pytest.mark.integration


SAMPLE = (
    "# /// script\n"
    "# dependencies = []\n"
    "# ///\n"
    "\n"
    "# %% [markdown]\n"
    "# # Parity\n"
    "\n"
    '# %% tags=["jc.step", "name=hi"]\n'
    "print('from the cell')\n"
)


def _project(tmp_path: Path) -> Project:
    cfg = default_config("parity")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "site", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    project = Project(root=tmp_path.resolve(), config=cfg)
    nb = project.notebooks_dir / "p.py"
    nb.write_text(SAMPLE, encoding="utf-8")
    runner = Runner(project)
    try:
        runner.run(nb)
    finally:
        runner.close()
    return project


def test_static_and_server_html_are_identical(tmp_path: Path) -> None:
    """Post-unified-assets, static + server render should produce byte-equal HTML.

    Both use ``standalone=False`` and the shared ``site/_assets/`` mount, so
    `_assets/…` hrefs resolve in both modes without any server-side trickery.
    """
    project = _project(tmp_path)

    # Static: write site/p.html via Renderer directly.
    with Renderer(project, standalone=False) as r:
        static_path = r.render_notebook(project.notebooks_dir / "p.py")
    static_html = static_path.output_path.read_text(encoding="utf-8")

    # Server: fetch via TestClient.
    with TestClient(build_app(project)) as client:
        resp = client.get("/p.html")
        assert resp.status_code == 200
        served_html = resp.text

    assert static_html == served_html, (
        "static and server render diverged — did one path change without the other?"
    )


def test_static_and_server_index_are_identical(tmp_path: Path) -> None:
    project = _project(tmp_path)

    with Renderer(project, standalone=False) as r:
        static_index = r.render_index()
    static_html = static_index.output_path.read_text(encoding="utf-8")

    with TestClient(build_app(project)) as client:
        served_html = client.get("/").text

    # Index pages reference timestamps from cache — mask them for the diff.
    import re

    timestamp_re = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[.\d]*\+\d{2}:\d{2}")
    static_masked = timestamp_re.sub("<ts>", static_html)
    served_masked = timestamp_re.sub("<ts>", served_html)
    assert static_masked == served_masked
