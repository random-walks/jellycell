"""Notebook + manifests → self-contained HTML.

Spec §2.6 pipeline:

1. Parse notebook (format.parse).
2. Match cells to cached manifests.
3. Render each cell via jinja partial; outputs via :mod:`jellycell.render.outputs`.
4. Assemble via :file:`templates/page.html.j2`.
5. Write to ``<reports>/<notebook-stem>.html``.

``--standalone`` mode base64-inlines image blobs instead of writing
external assets.
"""

from __future__ import annotations

import html as html_std
import re
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType

from jinja2 import Environment, PackageLoader, select_autoescape
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer

from jellycell.cache.index import CacheIndex
from jellycell.cache.manifest import Manifest
from jellycell.cache.store import CacheStore
from jellycell.format import parse as format_parse
from jellycell.format.cells import Cell
from jellycell.paths import Project
from jellycell.render.manuscript import ManuscriptLink, discover_manuscripts
from jellycell.render.markdown import render_markdown
from jellycell.render.outputs import render_output

_PYGMENTS_STYLE = "friendly"
_HEADER_RE = re.compile(r"^\s*(#{1,3})\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class RenderedNotebook:
    """Outcome of rendering a single notebook."""

    notebook: str
    """Path of the source notebook, relative to project root."""

    output_path: Path
    """Path where the HTML would be / was written.

    When ``write_pages=False`` the file is *not* actually created; the
    path is still reported so callers know where the canonical artifact
    would live in a static render. The HTML text is in :attr:`html`.
    """

    cell_count: int
    cached_count: int

    html: str | None = None
    """Rendered HTML string — populated when the Renderer was created with
    ``write_pages=False`` (server path). ``None`` in the default CLI
    ``jellycell render`` flow where the file at :attr:`output_path` is
    authoritative."""


@dataclass(frozen=True)
class RenderedIndex:
    """Outcome of rendering the project index page.

    Mirrors :class:`RenderedNotebook` so the server can fetch the HTML
    string directly (``write_pages=False``) without touching disk.
    """

    output_path: Path
    html: str | None = None


@dataclass(frozen=True)
class TocItem:
    """A single table-of-contents entry for the notebook sidebar."""

    anchor: str
    label: str
    level: int
    kind: str


@dataclass(frozen=True)
class SiblingNotebook:
    """Adjacent-notebook link data for cross-navigation."""

    href: str
    title: str
    current: bool


@dataclass(frozen=True)
class RendererEnv:
    """Shared long-lived state for the rendering pipeline.

    The Jinja environment (with compiled templates) and the Pygments CSS
    are expensive to build and completely stateless across requests —
    perfect to keep alive for the life of a server process. The
    ``CacheStore`` and ``CacheIndex`` are deliberately **not** here;
    those are opened per-render for simple SQLite thread safety.

    ``assets_dir`` is captured at env-build time so the live server
    points at ``.jellycell/cache/assets/`` while static ``jellycell
    render`` stays with ``site/_assets/``.
    """

    jinja: Environment
    pygments_css: str
    assets_dir: Path

    @classmethod
    def for_static(cls, project: Project) -> RendererEnv:
        """Env for ``jellycell render`` — assets under ``site/_assets/``."""
        return cls(
            jinja=_make_jinja_env(),
            pygments_css=_make_pygments_css(),
            assets_dir=project.site_dir / "_assets",
        )

    @classmethod
    def for_server(cls, project: Project) -> RendererEnv:
        """Env for ``jellycell view`` — assets under ``.jellycell/cache/assets/``
        (served by the ``/_assets/`` static mount). Live server is
        disk-write-free for HTML pages; assets still land on disk as
        content-hashed blobs so the static mount has something to serve.
        """
        return cls(
            jinja=_make_jinja_env(),
            pygments_css=_make_pygments_css(),
            assets_dir=project.cache_dir / "assets",
        )


def _make_jinja_env() -> Environment:
    return Environment(
        loader=PackageLoader("jellycell.render", "templates"),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _make_pygments_css() -> str:
    css = HtmlFormatter(style=_PYGMENTS_STYLE).get_style_defs(".jc-code")
    return str(css)


class Renderer:
    """Converts notebooks + cached manifests into a browsable HTML catalogue.

    Pass ``write_pages=False`` to skip writing HTML files to disk (the
    live server uses this mode and returns the HTML string directly via
    :attr:`RenderedNotebook.html`).

    Pass ``env=RendererEnv.for_server(project)`` in the server to reuse a
    long-lived Jinja environment across requests; the default builds a
    fresh env which is appropriate for the one-shot CLI path.
    """

    def __init__(
        self,
        project: Project,
        *,
        standalone: bool = False,
        env: RendererEnv | None = None,
        write_pages: bool = True,
    ) -> None:
        self.project = project
        self.standalone = standalone
        self.write_pages = write_pages
        self.env_data = env or RendererEnv.for_static(project)
        # Per-render handles — short-lived by design for SQLite thread safety.
        self.store = CacheStore(project.cache_dir)
        self.index = CacheIndex(project.cache_dir / "state.db")
        # Preserve the historical public attributes so existing callers
        # (templates, tests) keep working without edits.
        self.env = self.env_data.jinja
        self._pygments_css = self.env_data.pygments_css

    # ------------------------------------------------------------ high level
    def render_notebook(self, notebook_path: Path) -> RenderedNotebook:
        """Render a single notebook to ``site/<stem>.html``. Returns the result.

        With ``write_pages=True`` (the default) the HTML is written to
        ``site/<stem>.html`` and :attr:`RenderedNotebook.html` is ``None``.
        With ``write_pages=False`` (server path) disk is untouched and the
        rendered string is returned via :attr:`RenderedNotebook.html`.
        """
        nb = format_parse(notebook_path)
        notebook_rel = str(notebook_path.relative_to(self.project.root))
        stem = notebook_path.stem

        manifests = self._collect_manifests(notebook_rel)

        output_path = self.project.site_dir / f"{stem}.html"
        if self.write_pages:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        # Assets dir is captured at env-build time: `site/_assets/` for the
        # static CLI path, `.jellycell/cache/assets/` for the live server.
        assets_dir = self.env_data.assets_dir

        cells_html: list[str] = []
        cached_count = 0
        toc: list[TocItem] = []
        for ordinal, cell in enumerate(nb.cells):
            cell_id = f"{stem}:{ordinal}"
            manifest = manifests.get(cell_id)
            if manifest is not None:
                cached_count += 1
            toc.extend(_build_toc_for_cell(cell, ordinal))
            cells_html.append(self._render_cell(cell, ordinal, manifest, assets_dir))

        siblings = self._collect_siblings(notebook_path)
        prev_nb, next_nb = _prev_next(siblings)

        # Tearsheet cross-link: if manuscripts/tearsheets/<stem>.md exists,
        # the notebook page grows a "Tearsheet →" pointer — agents doing
        # dashboard review and humans flipping between source + summary
        # stay one click apart. Only wired when the file is actually on
        # disk; absent → no link rendered.
        tearsheet_link = self._tearsheet_link_for(stem)

        page = self.env.get_template("page.html.j2").render(
            title=stem,
            notebook=notebook_rel,
            project_name=self.project.config.project.name,
            cells_html="\n".join(cells_html),
            pygments_css=self._pygments_css,
            standalone=self.standalone,
            toc=toc,
            siblings=siblings,
            prev_nb=prev_nb,
            next_nb=next_nb,
            tearsheet_link=tearsheet_link,
        )
        if self.write_pages:
            output_path.write_text(page, encoding="utf-8")
        return RenderedNotebook(
            notebook=notebook_rel,
            output_path=output_path,
            cell_count=len(nb.cells),
            cached_count=cached_count,
            html=None if self.write_pages else page,
        )

    def render_index(self) -> RenderedIndex:
        """Render a project-level index listing every notebook + recent cache entries.

        Returns a :class:`RenderedIndex`. ``write_pages=True`` (default)
        writes ``site/index.html`` to disk; ``write_pages=False`` stashes
        the HTML in :attr:`RenderedIndex.html` without touching disk.
        """
        if self.write_pages:
            self.project.site_dir.mkdir(parents=True, exist_ok=True)
        notebook_paths = sorted(self.project.notebooks_dir.rglob("*.py"))
        notebooks = []
        for path in notebook_paths:
            rel = str(path.relative_to(self.project.root))
            entries = self.index.list_by_notebook(rel)
            notebooks.append(
                {
                    "href": f"{path.stem}.html",
                    "title": path.stem,
                    "path": rel,
                    "cell_count": len(entries),
                    "last_run": entries[-1]["executed_at"] if entries else None,
                }
            )
        recent_raw = self.index.list_all()[:20]
        recent: list[dict[str, object]] = []
        for row in recent_raw:
            nb_path = str(row["notebook"])
            recent.append(
                {
                    **row,
                    # Use the notebook's stem, not a fragile prefix/suffix replace.
                    "href": f"{Path(nb_path).stem}.html",
                }
            )
        # Manuscripts + tearsheets + journal land in a dedicated section on
        # the index. Server mode shows them live-reloading; static mode emits
        # plain-text links that work on GitHub as-is (no render).
        catalog = discover_manuscripts(self.project)
        page = self.env.get_template("index.html.j2").render(
            project_name=self.project.config.project.name,
            notebooks=notebooks,
            recent_runs=recent,
            pygments_css=self._pygments_css,
            catalog=catalog,
        )
        output = self.project.site_dir / "index.html"
        if self.write_pages:
            output.write_text(page, encoding="utf-8")
        return RenderedIndex(
            output_path=output,
            html=None if self.write_pages else page,
        )

    def render_all(self) -> list[RenderedNotebook]:
        """Render every notebook in the project plus the index."""
        results = []
        for path in sorted(self.project.notebooks_dir.rglob("*.py")):
            results.append(self.render_notebook(path))
        self.render_index()
        return results

    # ------------------------------------------------------------ internals
    def _tearsheet_link_for(self, stem: str) -> ManuscriptLink | None:
        """Return the tearsheet link matching ``stem`` if one exists on disk."""
        candidate = self.project.manuscripts_dir / "tearsheets" / f"{stem}.md"
        if not candidate.is_file():
            return None
        return ManuscriptLink(
            rel=f"tearsheets/{stem}.md",
            href=f"/manuscripts/tearsheets/{stem}.md",
            title=stem.replace("_", " ").replace("-", " ").title(),
            kind="tearsheet",
        )

    def _collect_siblings(self, current: Path) -> list[SiblingNotebook]:
        siblings: list[SiblingNotebook] = []
        for path in sorted(self.project.notebooks_dir.rglob("*.py")):
            is_current = path.resolve() == current.resolve()
            siblings.append(
                SiblingNotebook(
                    href=f"{path.stem}.html",
                    title=path.stem,
                    current=is_current,
                )
            )
        return siblings

    def _collect_manifests(self, notebook_rel: str) -> dict[str, Manifest]:
        entries = self.index.list_by_notebook(notebook_rel)
        manifests: dict[str, Manifest] = {}
        for row in entries:
            try:
                m = self.store.get_manifest(row["cache_key"])
            except KeyError:
                continue
            manifests[m.cell_id] = m
        return manifests

    def _render_cell(
        self,
        cell: Cell,
        ordinal: int,
        manifest: Manifest | None,
        assets_dir: Path,
    ) -> str:
        if cell.cell_type == "markdown":
            source_html = render_markdown(cell.source)
            kind = "markdown"
        elif cell.cell_type == "code":
            source_html = highlight(
                cell.source,
                PythonLexer(),
                HtmlFormatter(cssclass="jc-code", style=_PYGMENTS_STYLE),
            )
            kind = "code"
        else:
            source_html = f"<pre>{html_std.escape(cell.source)}</pre>"
            kind = "raw"

        outputs_html = ""
        if manifest is not None and manifest.outputs:
            outputs_html = "\n".join(
                render_output(o, store=self.store, assets_dir=assets_dir, inline=self.standalone)
                for o in manifest.outputs
            )

        artifacts: list[dict[str, object]] = []
        if manifest is not None:
            for art in manifest.artifacts:
                artifacts.append(
                    {
                        "path": art.path,
                        "href": f"/{art.path}",
                        "basename": Path(art.path).name,
                        "size_human": _human_size(art.size),
                        "mime": art.mime,
                    }
                )

        return self.env.get_template("partials/cell.html.j2").render(
            ordinal=ordinal,
            kind=kind,
            source_html=source_html,
            outputs_html=outputs_html,
            manifest=manifest,
            cell=cell,
            artifacts=artifacts,
        )

    # -------------------------------------------------------------- lifetime
    def close(self) -> None:
        """Close cache store + index."""
        self.store.close()
        self.index.close()

    def __enter__(self) -> Renderer:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


def _build_toc_for_cell(cell: Cell, ordinal: int) -> list[TocItem]:
    """Extract TOC entries from a cell.

    - Markdown cells contribute H1/H2/H3 headings.
    - Named code cells contribute one entry with the cell name.
    - Anonymous code cells are skipped (too noisy).
    """
    items: list[TocItem] = []
    anchor = f"cell-{ordinal}"
    if cell.cell_type == "markdown":
        for match in _HEADER_RE.finditer(cell.source):
            level = len(match.group(1))
            label = match.group(2).strip()
            if label:
                items.append(TocItem(anchor=anchor, label=label, level=level, kind="heading"))
    elif cell.cell_type == "code" and cell.spec.name:
        items.append(TocItem(anchor=anchor, label=cell.spec.name, level=3, kind="code"))
    return items


def _prev_next(
    siblings: list[SiblingNotebook],
) -> tuple[SiblingNotebook | None, SiblingNotebook | None]:
    """Find the prev/next notebook relative to the current one."""
    prev_nb: SiblingNotebook | None = None
    next_nb: SiblingNotebook | None = None
    for i, s in enumerate(siblings):
        if s.current:
            if i > 0:
                prev_nb = siblings[i - 1]
            if i + 1 < len(siblings):
                next_nb = siblings[i + 1]
            break
    return prev_nb, next_nb


def _human_size(n: int) -> str:
    """Format byte counts as `123 B`, `4.2 KB`, `1.7 MB`, etc."""
    if n < 1024:
        return f"{n} B"
    if n < 1024**2:
        return f"{n / 1024:.1f} KB"
    if n < 1024**3:
        return f"{n / 1024**2:.1f} MB"
    return f"{n / 1024**3:.1f} GB"
