"""The live viewer never writes HTML pages to disk.

These are the regression tests for the server's disk-write-free + response-
cached refactor. They assert three things that matter to DX:

1. `jellycell view` requests never populate `site/` — only `jellycell
   render` does. The live server reads inputs (notebooks, manifests) and
   returns HTML strings without leaving breadcrumbs.
2. Image assets land in `.jellycell/cache/assets/`, not
   `site/_assets/`, under the live server. (Static render still uses
   `site/_assets/` — covered by `test_render_parity.py`.)
3. The in-memory response cache short-circuits unchanged requests. A
   second request for the same notebook at the same view-key renders
   exactly once; changing the notebook's source invalidates the cache
   automatically via the key comparison. ``JELLYCELL_VIEW_NOCACHE=1``
   disables the cache for developers iterating on templates.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from jellycell.config import default_config
from jellycell.paths import Project
from jellycell.server.app import build_app

pytestmark = pytest.mark.integration


_TINY_NOTEBOOK = (
    "# /// script\n"
    "# dependencies = []\n"
    "# ///\n"
    "\n"
    "# %% [markdown]\n"
    "# # Tour\n"
    "\n"
    '# %% tags=["jc.step", "name=hello"]\n'
    "print('hi')\n"
)


def _bootstrap(tmp_path: Path) -> Project:
    cfg = default_config("no-disk")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "site", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    project = Project(root=tmp_path.resolve(), config=cfg)
    (project.notebooks_dir / "tour.py").write_text(_TINY_NOTEBOOK, encoding="utf-8")
    return project


class TestNoPagesOnDisk:
    def test_view_nb_does_not_write_site_html(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        assert not (project.site_dir / "tour.html").exists()
        with TestClient(build_app(project)) as client:
            r = client.get("/nb/tour")
        assert r.status_code == 200
        assert "Tour" in r.text
        # Key assertion: the server handled the request without writing
        # to site/, so nothing materializes.
        assert not (project.site_dir / "tour.html").exists()

    def test_view_index_does_not_write_site_html(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        assert not (project.site_dir / "index.html").exists()
        with TestClient(build_app(project)) as client:
            r = client.get("/")
        assert r.status_code == 200
        assert not (project.site_dir / "index.html").exists()

    def test_assets_mount_points_at_cache_not_site(self, tmp_path: Path) -> None:
        """``/_assets/`` serves from ``.jellycell/cache/assets/``, not ``site/_assets/``.

        The fixture writes a tiny blob at the cache-asset path; requesting
        it via ``/_assets/<name>`` must succeed.
        """
        project = _bootstrap(tmp_path)
        cache_assets = project.cache_dir / "assets"
        cache_assets.mkdir(parents=True, exist_ok=True)
        (cache_assets / "probe.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        # site/_assets/ deliberately does NOT contain the file — proves the
        # server isn't fallback-mounting it.
        assert not (project.site_dir / "_assets" / "probe.png").exists()

        with TestClient(build_app(project)) as client:
            r = client.get("/_assets/probe.png")
        assert r.status_code == 200
        assert r.content.startswith(b"\x89PNG")


class TestResponseCache:
    def test_second_request_reuses_cache_on_unchanged_notebook(self, tmp_path: Path) -> None:
        """Two GETs with no edits in between share the same rendered HTML.

        We can't easily hook into Renderer counter from outside, so we
        prove cache behavior by (a) asserting the responses are identical
        and (b) inspecting state directly — the cache dict must have an
        entry keyed by the notebook stem.
        """
        project = _bootstrap(tmp_path)
        app = build_app(project)
        with TestClient(app) as client:
            r1 = client.get("/nb/tour")
            r2 = client.get("/nb/tour")
        assert r1.text == r2.text
        # The app exposes its state via a private attr on the Starlette
        # instance; we peek at it deliberately in this regression test to
        # confirm the cache grew.
        state = _state_from_app(app)
        assert "tour" in state._response_cache

    def test_source_edit_invalidates_cache(self, tmp_path: Path) -> None:
        """Editing the notebook changes its view-key → next GET re-renders."""
        project = _bootstrap(tmp_path)
        app = build_app(project)
        with TestClient(app) as client:
            _ = client.get("/nb/tour")
            state = _state_from_app(app)
            key_before = state._response_cache["tour"].key

            # Edit the notebook's bytes — different source, new key.
            (project.notebooks_dir / "tour.py").write_text(
                _TINY_NOTEBOOK + "\n# extra trailing comment\n", encoding="utf-8"
            )
            _ = client.get("/nb/tour")

        state = _state_from_app(app)
        key_after = state._response_cache["tour"].key
        assert key_before != key_after, "view-key should change when the notebook's source changes"


class TestNoCacheEscape:
    def test_nocache_env_var_disables_cache(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``JELLYCELL_VIEW_NOCACHE=1`` → every request re-renders; cache dict stays empty."""
        monkeypatch.setenv("JELLYCELL_VIEW_NOCACHE", "1")
        project = _bootstrap(tmp_path)
        app = build_app(project)
        with TestClient(app) as client:
            r1 = client.get("/nb/tour")
            r2 = client.get("/nb/tour")
        assert r1.status_code == 200
        assert r2.status_code == 200
        state = _state_from_app(app)
        assert state._response_cache == {}


class TestStaticStillWrites:
    def test_jellycell_render_still_writes_site_html(self, tmp_path: Path) -> None:
        """CLI-path rendering (the default ``write_pages=True``) is unchanged."""
        from jellycell.render import Renderer

        project = _bootstrap(tmp_path)
        nb = project.notebooks_dir / "tour.py"
        with Renderer(project) as r:
            r.render_notebook(nb)
        # Static render writes to site/ as before.
        assert (project.site_dir / "tour.html").exists()


# ------------------------------------------------------------- helpers


def _state_from_app(app: object) -> object:
    """Pull out the ``_ServerState`` from a built Starlette app.

    The state is captured by closure in each route's endpoint. The
    cleanest hook is the project-index handler: its closure's
    ``state`` cell holds the live instance shared across all routes.
    """
    from starlette.applications import Starlette

    assert isinstance(app, Starlette)
    for route in app.routes:
        endpoint = getattr(route, "endpoint", None)
        if endpoint is None:
            continue
        # The handler closures were returned from factories like _index,
        # _notebook, etc. We can reach the captured state via __closure__.
        closure = getattr(endpoint, "__closure__", None) or ()
        for cell in closure:
            contents = cell.cell_contents
            if hasattr(contents, "_response_cache") and hasattr(contents, "project"):
                return contents
    raise AssertionError("couldn't locate _ServerState via closure walk")


# Suppress unused-import warning for os module (kept for explicit env reset)
_ = os
