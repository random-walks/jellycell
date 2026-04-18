"""Manuscript rendering for the live viewer.

Renders any ``.md`` file under ``manuscripts/`` as a standalone HTML page
using the project's template stack. Used by ``/manuscripts/<path>`` and
``/journal`` in :mod:`jellycell.server.app`.

Authored files at the root and auto-generated tearsheets under
``tearsheets/`` are treated identically at the render layer — the split
is a human / tooling convention, not a rendering one. The
:func:`discover_manuscripts` helper surfaces both groups plus the
optional journal entry so sidebars and index pages can link them.

No disk writes: this module is server-only. Static
``jellycell render`` leaves manuscripts alone on purpose — GitHub
renders them natively, and the tearsheet subfolder is designed for that.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from jellycell.paths import Project
from jellycell.render.markdown import render_markdown

if TYPE_CHECKING:
    from jinja2 import Environment


@dataclass(frozen=True)
class ManuscriptLink:
    """A single manuscript entry for sidebars and index pages."""

    rel: str
    """Path relative to ``manuscripts/`` (e.g. ``paper.md``)."""

    href: str
    """Server URL for the rendered page (e.g. ``/manuscripts/paper.md``)."""

    title: str
    """Display label — stem with underscores + hyphens humanized."""

    kind: str
    """One of ``authored``, ``tearsheet``, ``journal``."""

    current: bool = False
    """True when this link points to the manuscript currently being viewed."""


@dataclass(frozen=True)
class ManuscriptCatalog:
    """Organized view of every ``.md`` under ``manuscripts/``."""

    authored: list[ManuscriptLink] = field(default_factory=list)
    """Root-level hand-authored manuscripts (paper.md, findings.md, etc.)."""

    tearsheets: list[ManuscriptLink] = field(default_factory=list)
    """Auto-generated tearsheets under ``manuscripts/tearsheets/``."""

    journal: ManuscriptLink | None = None
    """The journal entry, if one exists (``journal.md`` or custom path)."""

    @property
    def has_any(self) -> bool:
        """True when the project has any manuscript worth linking."""
        return bool(self.authored or self.tearsheets or self.journal)


def discover_manuscripts(
    project: Project, *, current_rel: str | None = None
) -> ManuscriptCatalog:
    """Walk ``manuscripts/`` and classify each ``.md`` file.

    Classification rules:

    - A file at ``tearsheets/*.md`` is a tearsheet.
    - The file matching ``[journal] path`` (default ``journal.md``) is the
      journal — surfaced separately regardless of location.
    - Everything else at the root (or in other subfolders) is authored.

    The ``README.md`` is intentionally treated as authored — it's a
    human-written index for the folder.
    """
    md_dir = project.manuscripts_dir
    if not md_dir.exists():
        return ManuscriptCatalog()

    journal_rel = project.config.journal.path
    authored: list[ManuscriptLink] = []
    tearsheets: list[ManuscriptLink] = []
    journal: ManuscriptLink | None = None

    for md in sorted(md_dir.rglob("*.md")):
        rel = md.relative_to(md_dir).as_posix()
        link = _make_link(rel, kind="authored", current_rel=current_rel)
        if rel == journal_rel:
            journal = ManuscriptLink(
                rel=link.rel,
                href="/journal",
                title="Journal",
                kind="journal",
                current=link.current,
            )
        elif rel.startswith("tearsheets/"):
            tearsheets.append(
                ManuscriptLink(
                    rel=link.rel,
                    href=link.href,
                    title=link.title,
                    kind="tearsheet",
                    current=link.current,
                )
            )
        else:
            authored.append(link)

    return ManuscriptCatalog(authored=authored, tearsheets=tearsheets, journal=journal)


def _make_link(rel: str, *, kind: str, current_rel: str | None) -> ManuscriptLink:
    stem = Path(rel).stem
    title = stem.replace("_", " ").replace("-", " ").title()
    return ManuscriptLink(
        rel=rel,
        href=f"/manuscripts/{rel}",
        title=title,
        kind=kind,
        current=(current_rel == rel),
    )


def render_manuscript_page(
    project: Project,
    md_rel: str,
    *,
    env: Environment,
    pygments_css: str,
) -> str:
    """Render ``manuscripts/<md_rel>`` (plus sidebar + chrome) into an HTML string.

    Args:
        project: Current project — used to read the file + build catalog.
        md_rel: Path relative to ``manuscripts/`` (e.g. ``tearsheets/analysis.md``).
        env: Jinja environment from the renderer (reuses loader + filters).
        pygments_css: Pre-rendered pygments styles so fenced code blocks pick up
            the site theme when the markdown includes them.

    Raises:
        FileNotFoundError: If ``<manuscripts>/<md_rel>`` doesn't exist.
    """
    source = project.manuscripts_dir / md_rel
    if not source.is_file():
        raise FileNotFoundError(md_rel)

    body_html = render_markdown(source.read_text(encoding="utf-8"))
    catalog = discover_manuscripts(project, current_rel=md_rel)
    tearsheet_for = _tearsheet_source_notebook(project, md_rel)

    return env.get_template("manuscript.html.j2").render(
        project_name=project.config.project.name,
        md_rel=md_rel,
        md_title=Path(md_rel).stem.replace("_", " ").replace("-", " ").title(),
        body_html=body_html,
        catalog=catalog,
        tearsheet_for=tearsheet_for,
        prev_link=_adjacent(catalog, md_rel, offset=-1),
        next_link=_adjacent(catalog, md_rel, offset=+1),
        pygments_css=pygments_css,
    )


def render_manuscripts_index(
    project: Project, *, env: Environment, pygments_css: str
) -> str:
    """Render the ``/manuscripts/`` landing page listing every manuscript."""
    catalog = discover_manuscripts(project)
    return env.get_template("manuscripts_index.html.j2").render(
        project_name=project.config.project.name,
        catalog=catalog,
        pygments_css=pygments_css,
    )


def _tearsheet_source_notebook(project: Project, md_rel: str) -> str | None:
    """When viewing a tearsheet, return the stem of its source notebook (if any)."""
    if not md_rel.startswith("tearsheets/"):
        return None
    stem = Path(md_rel).stem
    for nb in project.notebooks_dir.rglob("*.py"):
        if nb.stem == stem:
            return stem
    return None


def _adjacent(
    catalog: ManuscriptCatalog, md_rel: str, *, offset: int
) -> ManuscriptLink | None:
    """Return the previous or next tearsheet when browsing tearsheets in order.

    Authored manuscripts and the journal don't get prev/next navigation —
    they're read as standalone documents. Tearsheets, however, form a
    coherent sequence per project (often numbered 01-, 02-, etc.) so the
    reader expects to flip through them.
    """
    if not md_rel.startswith("tearsheets/"):
        return None
    items = catalog.tearsheets
    for i, item in enumerate(items):
        if item.rel == md_rel:
            j = i + offset
            if 0 <= j < len(items):
                return items[j]
            return None
    return None


__all__ = [
    "ManuscriptCatalog",
    "ManuscriptLink",
    "discover_manuscripts",
    "render_manuscript_page",
    "render_manuscripts_index",
]
