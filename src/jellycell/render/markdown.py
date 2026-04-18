"""Markdown rendering with MyST plugins enabled.

Thin wrapper around :mod:`markdown_it` + :mod:`mdit_py_plugins`. Shared
between the renderer (cell markdown) and future doc-site integration.
"""

from __future__ import annotations

from markdown_it import MarkdownIt
from mdit_py_plugins.deflist import deflist_plugin
from mdit_py_plugins.tasklists import tasklists_plugin


def _make_parser() -> MarkdownIt:
    md = (
        MarkdownIt("commonmark", {"html": False, "linkify": True, "typographer": True})
        .enable("table")
        .enable("strikethrough")
        .use(deflist_plugin)
        .use(tasklists_plugin)
    )
    return md


_PARSER = _make_parser()


def render_markdown(text: str) -> str:
    """Render markdown ``text`` to safe HTML."""
    rendered: str = _PARSER.render(text)
    return rendered
