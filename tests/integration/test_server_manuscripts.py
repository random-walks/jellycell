"""`/manuscripts/`, `/manuscripts/<path>`, `/journal` routes + cross-links.

Covers the live-viewer lifts: dynamic markdown rendering, discovery of
authored + tearsheet files, the journal alias, the tearsheet ↔ notebook
cross-link on notebook pages, prev/next between tearsheets, and the
state-API payload enrichment.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from starlette.testclient import TestClient

from jellycell.config import default_config
from jellycell.paths import Project
from jellycell.render.manuscript import discover_manuscripts
from jellycell.server.app import build_app
from jellycell.server.watch import map_change

pytestmark = pytest.mark.integration


# ------------------------------------------------------------- bootstrap


def _bootstrap(tmp_path: Path) -> Project:
    cfg = default_config("srv-ms")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "reports", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    return Project(root=tmp_path.resolve(), config=cfg)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ------------------------------------------------------------- catalog discovery


class TestDiscover:
    def test_empty_project(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        catalog = discover_manuscripts(project)
        assert not catalog.has_any

    def test_classifies_authored_tearsheet_journal(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        _write(project.manuscripts_dir / "paper.md", "# Paper\n")
        _write(project.manuscripts_dir / "tearsheets" / "analysis.md", "# Analysis\n")
        _write(project.manuscripts_dir / "journal.md", "# Journal\n")
        catalog = discover_manuscripts(project)
        assert [link.rel for link in catalog.authored] == ["paper.md"]
        assert [link.rel for link in catalog.tearsheets] == ["tearsheets/analysis.md"]
        assert catalog.journal is not None
        assert catalog.journal.href == "/journal"

    def test_current_flag_marks_active_link(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        _write(project.manuscripts_dir / "a.md", "# A\n")
        _write(project.manuscripts_dir / "b.md", "# B\n")
        catalog = discover_manuscripts(project, current_rel="a.md")
        active = {link.rel: link.current for link in catalog.authored}
        assert active == {"a.md": True, "b.md": False}


# ------------------------------------------------------------- server routes


def _client(project: Project) -> TestClient:
    return TestClient(build_app(project))


class TestManuscriptRoutes:
    def test_manuscripts_index_lists_each_kind(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        _write(project.manuscripts_dir / "paper.md", "# Paper draft\n")
        _write(project.manuscripts_dir / "tearsheets" / "analysis.md", "# Analysis\n")
        _write(project.manuscripts_dir / "journal.md", "# Journal\n")
        with _client(project) as client:
            r = client.get("/manuscripts/")
        assert r.status_code == 200
        assert "Paper" in r.text
        assert "Analysis" in r.text
        assert "Journal" in r.text

    def test_manuscript_page_renders_markdown(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        _write(
            project.manuscripts_dir / "paper.md",
            "# Paper\n\nBackground paragraph.\n",
        )
        with _client(project) as client:
            r = client.get("/manuscripts/paper.md")
        assert r.status_code == 200
        assert "<h1>Paper</h1>" in r.text
        assert "Background paragraph." in r.text

    def test_tearsheet_page_renders(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        _write(
            project.manuscripts_dir / "tearsheets" / "analysis.md",
            "# Analysis tearsheet\n\nJust testing.\n",
        )
        with _client(project) as client:
            r = client.get("/manuscripts/tearsheets/analysis.md")
        assert r.status_code == 200
        assert "Analysis tearsheet" in r.text

    def test_missing_manuscript_404(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        with _client(project) as client:
            r = client.get("/manuscripts/nope.md")
        assert r.status_code == 404

    def test_path_traversal_blocked(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        # Even if the file exists (hypothetically) under project root, we
        # refuse `..` paths before touching disk.
        with _client(project) as client:
            r = client.get("/manuscripts/../jellycell.toml")
        # Starlette normalizes URL path traversal; HTTPX/TestClient typically
        # sends the normalized form. Both 404 and 400 are acceptable outcomes.
        assert r.status_code >= 400


class TestJournalRoute:
    def test_journal_404_when_missing(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        with _client(project) as client:
            r = client.get("/journal")
        assert r.status_code == 404

    def test_journal_renders_when_present(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        _write(project.manuscripts_dir / "journal.md", "# Journal\n\n## entry one\n")
        with _client(project) as client:
            r = client.get("/journal")
        assert r.status_code == 200
        assert "entry one" in r.text


class TestTearsheetCrossLink:
    def test_notebook_page_links_to_existing_tearsheet(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        # Need a notebook that can be rendered. Minimal-source notebook so
        # the renderer produces HTML without needing a real run.
        (project.notebooks_dir / "tour.py").write_text(
            "# /// script\n# dependencies = []\n# ///\n\n# %% [markdown]\n# # Tour\n",
            encoding="utf-8",
        )
        _write(
            project.manuscripts_dir / "tearsheets" / "tour.md",
            "# Tour tearsheet\n",
        )
        with _client(project) as client:
            r = client.get("/nb/tour")
        assert r.status_code == 200
        # Cross-link text + href both present
        assert "Tearsheet →" in r.text
        assert "/manuscripts/tearsheets/tour.md" in r.text

    def test_notebook_page_omits_link_when_tearsheet_absent(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        (project.notebooks_dir / "tour.py").write_text(
            "# /// script\n# dependencies = []\n# ///\n\n# %% [markdown]\n# # Tour\n",
            encoding="utf-8",
        )
        with _client(project) as client:
            r = client.get("/nb/tour")
        assert r.status_code == 200
        assert "Tearsheet →" not in r.text


class TestPrevNextTearsheet:
    def test_prev_next_links_between_tearsheets(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        _write(project.manuscripts_dir / "tearsheets" / "01-explore.md", "# 01\n")
        _write(project.manuscripts_dir / "tearsheets" / "02-decompose.md", "# 02\n")
        _write(project.manuscripts_dir / "tearsheets" / "03-forecast.md", "# 03\n")
        with _client(project) as client:
            r = client.get("/manuscripts/tearsheets/02-decompose.md")
        assert r.status_code == 200
        assert "01-explore.md" in r.text
        assert "03-forecast.md" in r.text

    def test_authored_page_has_no_prevnext(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        _write(project.manuscripts_dir / "paper.md", "# Paper\n")
        _write(project.manuscripts_dir / "tearsheets" / "t1.md", "# T1\n")
        with _client(project) as client:
            r = client.get("/manuscripts/paper.md")
        # Tearsheet prev/next nav belongs to tearsheet pages only; authored
        # writeups are standalone docs.
        assert "Next tearsheet" not in r.text
        assert "Previous tearsheet" not in r.text


class TestStateApi:
    def test_state_includes_manuscripts(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        _write(project.manuscripts_dir / "paper.md", "# Paper\n")
        _write(project.manuscripts_dir / "tearsheets" / "analysis.md", "# An\n")
        _write(project.manuscripts_dir / "journal.md", "# J\n")
        with _client(project) as client:
            payload = client.get("/api/state.json").json()
        ms = payload["manuscripts"]
        assert [link["rel"] for link in ms["authored"]] == ["paper.md"]
        assert [link["rel"] for link in ms["tearsheets"]] == ["tearsheets/analysis.md"]
        assert ms["journal"]["href"] == "/journal"


class TestWatchMapping:
    def test_manuscript_md_maps_to_specific_route(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        path = project.manuscripts_dir / "tearsheets" / "analysis.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# T\n", encoding="utf-8")
        event = map_change(project, path)
        assert event is not None
        assert event.path == "/manuscripts/tearsheets/analysis.md"

    def test_journal_maps_to_journal_alias(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        path = project.manuscripts_dir / "journal.md"
        path.write_text("# J\n", encoding="utf-8")
        event = map_change(project, path)
        assert event is not None
        assert event.path == "/journal"

    def test_non_markdown_manuscript_is_ignored(self, tmp_path: Path) -> None:
        """A .txt scratchpad in manuscripts/ shouldn't trigger reloads."""
        project = _bootstrap(tmp_path)
        path = project.manuscripts_dir / "notes.txt"
        path.write_text("scratch\n", encoding="utf-8")
        event = map_change(project, path)
        assert event is None


# httpx import is kept for test-author convenience even when unused this pass.
_ = httpx
