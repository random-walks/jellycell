"""Python API for tearsheet-style manuscript generation.

Three helpers for producing curated markdown output from inside
``jc.step``-tagged cells — so the rendered document lives in the
content-addressed cache graph, rather than outside it (the
``jellycell export tearsheet`` CLI flow runs post-hoc and can drift).

The three match three common shapes of analyst output:

``jellycell.tearsheets.findings(results, *, out_path, project, ...)``
    Summary of one or more estimators' metrics. Renders each estimator
    as a two-column markdown table. Use when you have a dict of
    estimator → metrics and want a FINDINGS.md to commit.

``jellycell.tearsheets.methodology(spec, *, out_path, project, ...)``
    Procedural manuscript. Takes an ordered mapping of section title →
    markdown body and renders each as ``## section`` with the body
    beneath. Good for "how we did X" narratives.

``jellycell.tearsheets.audit(notebook, *, out_path, ...)``
    Per-notebook tearsheet (cells, artifacts, JSON summaries). Thin
    wrapper over :func:`jellycell.export.tearsheet.export_tearsheet`;
    reads manifests from the project's cache.

All three share a pinnable header (author, month_year, version, project)
via ``template_overrides`` for byte-stable regeneration. They return
the ``Path`` they wrote so callers can chain into downstream code.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jellycell.tearsheets._audit import audit
from jellycell.tearsheets._template import (
    ensure_output_path,
    render_header,
    render_key_value_table,
)

__all__ = ["audit", "findings", "methodology"]


def findings(
    results: Mapping[str, Mapping[str, Any]],
    *,
    out_path: str | Path,
    project: str,
    title: str = "Findings",
    subtitle: str = "Summary of estimator results from the current run.",
    template_overrides: dict[str, str] | None = None,
) -> Path:
    """Render a FINDINGS manuscript summarizing estimator results.

    Each top-level key in ``results`` becomes a ``## <estimator>``
    section with a two-column ``Metric | Value`` table. Nested dicts
    flatten with dotted keys (``{"cs": {"att": 0.2}}`` → ``cs.att``).

    Args:
        results: Mapping of estimator name to its metric mapping.
            Example: ``{"twfe": {"att": 0.2, "n_obs": 1234}, "cs": {...}}``.
            Values can be numbers, strings, bools, lists, None, or
            nested dicts.
        out_path: Destination markdown file. Parent dirs are created.
        project: Human-readable project name; goes in the header.
        title: H1 heading. Defaults to ``"Findings"``.
        subtitle: Subtitle paragraph under the H1.
        template_overrides: Pinnable header fields —
            ``{"author", "author_url", "month_year", "version"}``.
            Unspecified keys default to empty / now / jellycell version.

    Returns:
        The resolved ``Path`` that was written.

    Raises:
        ValueError: ``results`` is empty.
    """
    if not results:
        raise ValueError("findings(): results is empty; nothing to render.")

    target = ensure_output_path(out_path)
    parts: list[str] = [
        render_header(
            kind="findings",
            title=title,
            subtitle=subtitle,
            project=project,
            template_overrides=template_overrides,
        )
    ]
    for estimator, metrics in results.items():
        parts.append(f"## {estimator}\n\n")
        if not metrics:
            parts.append("*(no metrics recorded)*\n\n")
            continue
        parts.append(render_key_value_table(dict(metrics)))
        parts.append("\n")

    target.write_text("".join(parts).rstrip() + "\n", encoding="utf-8")
    return target


def methodology(
    spec: Mapping[str, str],
    *,
    out_path: str | Path,
    project: str,
    title: str = "Methodology",
    subtitle: str = "Procedural details for the analysis in this project.",
    template_overrides: dict[str, str] | None = None,
) -> Path:
    """Render a METHODOLOGY manuscript from an ordered section mapping.

    Each ``(section_title, markdown_body)`` entry in ``spec`` becomes a
    ``## section_title`` followed by its body verbatim. The body is
    plain markdown — you control the shape (paragraphs, lists, code
    fences, sub-headings via ``###``).

    Args:
        spec: Ordered mapping of section title to markdown body.
            Example: ``{"Data source": "The dataset is ...", "Estimators": "We use TWFE and CS ..."}``.
        out_path: Destination markdown file. Parent dirs are created.
        project: Human-readable project name; goes in the header.
        title: H1 heading. Defaults to ``"Methodology"``.
        subtitle: Subtitle paragraph under the H1.
        template_overrides: Pinnable header fields — same as
            :func:`findings`.

    Returns:
        The resolved ``Path`` that was written.

    Raises:
        ValueError: ``spec`` is empty.
    """
    if not spec:
        raise ValueError("methodology(): spec is empty; nothing to render.")

    target = ensure_output_path(out_path)
    parts: list[str] = [
        render_header(
            kind="methodology",
            title=title,
            subtitle=subtitle,
            project=project,
            template_overrides=template_overrides,
        )
    ]
    for section, body in spec.items():
        parts.append(f"## {section}\n\n")
        stripped = body.rstrip()
        if not stripped:
            parts.append("*(section left blank)*\n\n")
            continue
        parts.append(stripped + "\n\n")

    target.write_text("".join(parts).rstrip() + "\n", encoding="utf-8")
    return target
