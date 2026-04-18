"""Starlette ASGI app for ``jellycell view``.

Routes (all read-only):

- ``GET /`` → rendered project index (notebooks + manuscripts listing).
- ``GET /nb/<stem>`` → rendered notebook page.
- ``GET /manuscripts/`` → manuscripts index (authored + tearsheets + journal).
- ``GET /manuscripts/{path:path}`` → rendered markdown under ``manuscripts/``.
- ``GET /journal`` → alias for the configured journal file.
- ``GET /artifacts/<...>`` → static artifact serving.
- ``GET /api/state.json`` → catalogue state for agents.
- ``GET /events`` → SSE reload stream.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route
from starlette.staticfiles import StaticFiles

from jellycell.cache.index import CacheIndex
from jellycell.paths import Project
from jellycell.render import Renderer
from jellycell.render.manuscript import (
    discover_manuscripts,
    render_manuscript_page,
    render_manuscripts_index,
)
from jellycell.render.renderer import RendererEnv
from jellycell.server.sse import ReloadBroker, event_to_sse
from jellycell.server.watch import watch_project

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

#: Opt-out escape hatch for the response cache. Set in the environment when
#: developing templates — every request re-renders so edits appear without
#: bouncing the server.
_NOCACHE_ENV = "JELLYCELL_VIEW_NOCACHE"


def build_app(project: Project, *, broker: ReloadBroker | None = None) -> Starlette:
    """Assemble the live-viewer Starlette app for ``project``."""
    broker = broker or ReloadBroker()
    state = _ServerState(project=project, broker=broker)

    @asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        task = asyncio.create_task(watch_project(project, broker))
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    routes = [
        Route("/", endpoint=_index(state)),
        # The rendered notebook breadcrumb links to `index.html`; serve the same content.
        Route("/index.html", endpoint=_index(state)),
        Route("/nb/{stem}", endpoint=_notebook(state)),
        Route("/manuscripts/", endpoint=_manuscripts_index(state)),
        Route("/manuscripts/{path:path}", endpoint=_manuscript_page(state)),
        Route("/journal", endpoint=_journal(state)),
        # Links in the rendered index use relative `<stem>.html` hrefs so
        # the same HTML works as static files. Serve the same content here.
        Route("/{stem}.html", endpoint=_notebook(state)),
        Route("/api/state.json", endpoint=_state_json(state)),
        Route("/events", endpoint=_events(state)),
    ]
    # Live-mode assets live under `.jellycell/cache/assets/` — `RendererEnv.
    # for_server()` writes image blobs here as content-hashed files; the
    # `/_assets/` mount serves them back to notebook pages. `site/_assets/`
    # stays the static-CLI-only destination; the live server never touches
    # it, which is the whole point of this layout.
    assets_dir = state.env.assets_dir
    assets_dir.mkdir(parents=True, exist_ok=True)
    routes.append(_mount_static("/_assets", assets_dir))
    if project.artifacts_dir.exists():
        routes.append(
            _mount_static("/artifacts", project.artifacts_dir),
        )
    return Starlette(debug=False, lifespan=lifespan, routes=routes)


@dataclass
class _CachedResponse:
    """One entry in the server's per-notebook-stem response cache."""

    key: str
    html: str


class _ServerState:
    """Live-viewer state — long-lived Jinja env + response cache + broker.

    The env (Jinja templates + Pygments CSS + assets dir) is built once at
    app startup and reused across every request. Cache handles
    (``CacheStore`` / ``CacheIndex``) are still opened per render inside
    ``Renderer`` so SQLite stays thread-local — simpler than pooling.

    ``_response_cache`` is keyed by notebook stem (or the sentinel
    ``"__index__"`` for the project index). Each entry carries the
    ``notebook_view_key`` from ``CacheIndex`` — when the current key
    matches the cached one, the HTML is reused verbatim. Any edit to the
    notebook source or any new run invalidates the key, so the server
    always serves the up-to-date view without explicit cache busting.

    Set ``JELLYCELL_VIEW_NOCACHE=1`` in the environment to skip the cache
    entirely (handy when iterating on templates with the server running).
    """

    def __init__(self, project: Project, broker: ReloadBroker) -> None:
        self.project = project
        self.broker = broker
        self.env: RendererEnv = RendererEnv.for_server(project)
        self.env.assets_dir.mkdir(parents=True, exist_ok=True)
        self._response_cache: dict[str, _CachedResponse] = {}
        self._nocache = bool(os.environ.get(_NOCACHE_ENV))

    def render_notebook_html(self, stem: str) -> str:
        """Return the rendered HTML string for ``/nb/<stem>``.

        Hits the response cache when the notebook's view-key hasn't
        changed since the last render; otherwise re-renders with
        ``write_pages=False`` so ``site/<stem>.html`` stays unchanged.
        """
        path = self._find_notebook(stem)
        if path is None:
            raise FileNotFoundError(stem)

        index = CacheIndex(self.project.cache_dir / "state.db")
        try:
            key = index.notebook_view_key(
                self.project.root, str(path.relative_to(self.project.root))
            )
        finally:
            index.close()

        if not self._nocache and key is not None:
            cached = self._response_cache.get(stem)
            if cached is not None and cached.key == key:
                return cached.html

        with Renderer(self.project, env=self.env, write_pages=False) as r:
            result = r.render_notebook(path)
        html = result.html or ""  # result.html is always set when write_pages=False

        if not self._nocache and key is not None:
            self._response_cache[stem] = _CachedResponse(key=key, html=html)
        return html

    def render_index_html(self) -> str:
        """Return the rendered HTML string for ``/``.

        The index page's view-key is the sha256 of every notebook's
        view-key concatenated — changes anywhere in the project
        invalidate the cached index without tracking dependencies
        explicitly.
        """
        index_key = self._index_view_key()
        if not self._nocache and index_key is not None:
            cached = self._response_cache.get("__index__")
            if cached is not None and cached.key == index_key:
                return cached.html

        with Renderer(self.project, env=self.env, write_pages=False) as r:
            result = r.render_index()
        html = result.html or ""

        if not self._nocache and index_key is not None:
            self._response_cache["__index__"] = _CachedResponse(key=index_key, html=html)
        return html

    def _find_notebook(self, stem: str) -> Path | None:
        for path in self.project.notebooks_dir.rglob("*.py"):
            if path.stem == stem:
                return path
        return None

    def _index_view_key(self) -> str | None:
        """Derive an index-level view key by rolling up each notebook's key."""
        import hashlib

        index = CacheIndex(self.project.cache_dir / "state.db")
        try:
            parts: list[str] = []
            for path in sorted(self.project.notebooks_dir.rglob("*.py")):
                rel = str(path.relative_to(self.project.root))
                nk = index.notebook_view_key(self.project.root, rel)
                if nk is None:
                    return None
                parts.append(nk)
        finally:
            index.close()
        if not parts:
            return "empty"
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _index(state: _ServerState):  # type: ignore[no-untyped-def]
    async def handler(_request: Request) -> HTMLResponse:
        html = state.render_index_html()
        return HTMLResponse(html)

    return handler


def _notebook(state: _ServerState):  # type: ignore[no-untyped-def]
    async def handler(request: Request) -> HTMLResponse:
        stem = request.path_params["stem"]
        try:
            html = state.render_notebook_html(stem)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return HTMLResponse(html)

    return handler


def _manuscripts_index(state: _ServerState):  # type: ignore[no-untyped-def]
    """``/manuscripts/`` landing page — authored + tearsheets + journal listing."""

    async def handler(_request: Request) -> HTMLResponse:
        html = render_manuscripts_index(
            state.project,
            env=state.env.jinja,
            pygments_css=state.env.pygments_css,
        )
        return HTMLResponse(html)

    return handler


def _manuscript_page(state: _ServerState):  # type: ignore[no-untyped-def]
    """Render any ``manuscripts/<path>.md`` into an HTML page with the project shell."""

    async def handler(request: Request) -> HTMLResponse:
        rel = request.path_params["path"]
        # Security: forbid path escape out of manuscripts/. Catch both absolute
        # paths and ``..``-based traversal before touching the filesystem.
        if ".." in Path(rel).parts or Path(rel).is_absolute():
            raise HTTPException(status_code=404, detail=rel)
        try:
            html = render_manuscript_page(
                state.project,
                rel,
                env=state.env.jinja,
                pygments_css=state.env.pygments_css,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return HTMLResponse(html)

    return handler


def _journal(state: _ServerState):  # type: ignore[no-untyped-def]
    """Alias for the configured journal file — 404s cleanly when it doesn't exist yet."""

    async def handler(_request: Request) -> HTMLResponse:
        journal_rel = state.project.config.journal.path
        path = state.project.manuscripts_dir / journal_rel
        if not path.is_file():
            raise HTTPException(
                status_code=404,
                detail=(
                    f"no journal at manuscripts/{journal_rel} yet — "
                    "run `jellycell run <notebook>` once to create it."
                ),
            )
        html = render_manuscript_page(
            state.project,
            journal_rel,
            env=state.env.jinja,
            pygments_css=state.env.pygments_css,
        )
        return HTMLResponse(html)

    return handler


def _state_json(state: _ServerState):  # type: ignore[no-untyped-def]
    async def handler(_request: Request) -> JSONResponse:
        index = CacheIndex(state.project.cache_dir / "state.db")
        try:
            catalog = discover_manuscripts(state.project)
            payload = {
                "schema_version": 1,
                "project": state.project.config.project.name,
                "root": str(state.project.root),
                "recent_runs": index.list_all()[:50],
                "manuscripts": {
                    "authored": [asdict(link) for link in catalog.authored],
                    "tearsheets": [asdict(link) for link in catalog.tearsheets],
                    "journal": asdict(catalog.journal) if catalog.journal else None,
                },
            }
        finally:
            index.close()
        return JSONResponse(payload)

    return handler


def _events(state: _ServerState):  # type: ignore[no-untyped-def]
    from sse_starlette.sse import EventSourceResponse

    async def handler(_request: Request) -> EventSourceResponse:
        async def stream() -> AsyncIterator[dict[str, str]]:
            async for event in state.broker.subscribe():
                yield event_to_sse(event)

        return EventSourceResponse(stream())

    return handler


def _mount_static(prefix: str, directory: Path) -> Route:
    app = StaticFiles(directory=str(directory), check_dir=False)
    # Mount returns a Starlette mount, but we use Route-compatible tuple via a helper
    from starlette.routing import Mount

    return Mount(prefix, app=app)  # type: ignore[return-value]


__all__ = ["ReloadBroker", "build_app"]
