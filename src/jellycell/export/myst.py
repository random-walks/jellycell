"""Export jellycell notebook + cached manifests to MyST markdown.

Uses MyST's ``{code-cell}`` directive so downstream toolchains (Sphinx +
myst-nb, Jupyter Book) can render the notebook without re-execution.
"""

from __future__ import annotations

import json
from pathlib import Path

from jellycell.cache.manifest import (
    DisplayDataOutput,
    ErrorOutput,
    ExecuteResultOutput,
    Manifest,
    StreamOutput,
)
from jellycell.cache.store import CacheStore
from jellycell.format import parse as format_parse


def export_md(
    notebook_path: Path,
    manifests_by_cell: dict[str, Manifest],
    store: CacheStore,
    output_path: Path,
) -> Path:
    """Write ``notebook_path`` + cached outputs to ``output_path`` as MyST markdown."""
    nb = format_parse(notebook_path)
    stem = notebook_path.stem
    lines: list[str] = []

    lines.append("---")
    lines.append("jupytext:")
    lines.append("  text_representation:")
    lines.append("    extension: .md")
    lines.append("    format_name: myst")
    lines.append("kernelspec:")
    lines.append("  display_name: Python 3")
    lines.append("  language: python")
    lines.append("  name: python3")
    lines.append("---")
    lines.append("")

    for ordinal, cell in enumerate(nb.cells):
        if cell.cell_type == "markdown":
            lines.append(cell.source.rstrip("\n"))
            lines.append("")
        elif cell.cell_type == "code":
            manifest = manifests_by_cell.get(f"{stem}:{ordinal}")
            lines.append("```{code-cell} python")
            if cell.spec.name:
                lines.append(f":name: {cell.spec.name}")
            lines.append(cell.source.rstrip("\n"))
            lines.append("```")
            if manifest is not None:
                lines.extend(_render_output_block(manifest, store))
            lines.append("")
        else:
            lines.append("```")
            lines.append(cell.source.rstrip("\n"))
            lines.append("```")
            lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def _render_output_block(manifest: Manifest, store: CacheStore) -> list[str]:
    if not manifest.outputs:
        return []
    lines = [""]
    for o in manifest.outputs:
        if isinstance(o, StreamOutput):
            try:
                text = store.get_blob(o.blob).decode("utf-8", errors="replace")
            except KeyError:
                text = ""
            lines.append("```")
            lines.append(text.rstrip("\n"))
            lines.append("```")
        elif isinstance(o, DisplayDataOutput | ExecuteResultOutput):
            lines.append(f":::{{admonition}} {o.mime}")
            lines.append(":class: note")
            if o.mime == "text/plain":
                try:
                    text = store.get_blob(o.blob).decode("utf-8", errors="replace")
                except KeyError:
                    text = ""
                lines.append("```")
                lines.append(text.rstrip("\n"))
                lines.append("```")
            else:
                lines.append(f"*(output blob {o.blob[:12]}...)*")
            lines.append(":::")
        elif isinstance(o, ErrorOutput):
            lines.append(":::{error}")
            lines.append(f"**{o.ename}**: {o.evalue}")
            lines.append("```")
            lines.append("\n".join(o.traceback))
            lines.append("```")
            lines.append(":::")
    return lines


__all__ = ["export_md"]


# Silence "unused" import in some environments
_ = json
