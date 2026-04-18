"""Export jellycell notebook + cached manifests to ``.ipynb``.

The produced file opens in Jupyter/VSCode and shows cached outputs without
re-executing. Blobs are retrieved from the CacheStore and reattached as
nbformat output dicts.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import nbformat

from jellycell.cache.manifest import (
    DisplayDataOutput,
    ErrorOutput,
    ExecuteResultOutput,
    Manifest,
    StreamOutput,
)
from jellycell.cache.store import CacheStore
from jellycell.format import parse as format_parse


def export_ipynb(
    notebook_path: Path,
    manifests_by_cell: dict[str, Manifest],
    store: CacheStore,
    output_path: Path,
) -> Path:
    """Write ``notebook_path`` + cached outputs to ``output_path`` as ``.ipynb``.

    Args:
        notebook_path: Source jellycell ``.py`` notebook.
        manifests_by_cell: Map from ``cell_id`` (``<stem>:<ordinal>``) to the
            cached :class:`Manifest` for that cell (if any).
        store: Cache store for blob retrieval.
        output_path: Destination ``.ipynb`` path.

    Returns:
        ``output_path`` for convenience.
    """
    nb_source = format_parse(notebook_path)
    stem = notebook_path.stem
    nb = nbformat.v4.new_notebook()

    for ordinal, cell in enumerate(nb_source.cells):
        if cell.cell_type == "markdown":
            nb_cell = nbformat.v4.new_markdown_cell(cell.source)
        elif cell.cell_type == "code":
            nb_cell = nbformat.v4.new_code_cell(cell.source)
            manifest = manifests_by_cell.get(f"{stem}:{ordinal}")
            if manifest is not None:
                nb_cell.outputs = [
                    nbformat.from_dict(out) for out in _build_nbformat_outputs(manifest, store)
                ]
                if manifest.outputs:
                    nb_cell.execution_count = _last_execution_count(manifest)
        else:
            nb_cell = nbformat.v4.new_raw_cell(cell.source)

        for k, v in cell.metadata.items():
            nb_cell.metadata[k] = v
        nb.cells.append(nb_cell)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    return output_path


def _build_nbformat_outputs(manifest: Manifest, store: CacheStore) -> list[dict[str, Any]]:
    outs: list[dict[str, Any]] = []
    for o in manifest.outputs:
        if isinstance(o, StreamOutput):
            try:
                text = store.get_blob(o.blob).decode("utf-8", errors="replace")
            except KeyError:
                text = "(blob missing)"
            outs.append({"output_type": "stream", "name": o.name, "text": text})
        elif isinstance(o, DisplayDataOutput):
            outs.append(
                {
                    "output_type": "display_data",
                    "data": _load_mime_bundle(o.mime, o.blob, store),
                    "metadata": {},
                }
            )
        elif isinstance(o, ExecuteResultOutput):
            outs.append(
                {
                    "output_type": "execute_result",
                    "execution_count": o.execution_count,
                    "data": _load_mime_bundle(o.mime, o.blob, store),
                    "metadata": {},
                }
            )
        elif isinstance(o, ErrorOutput):
            outs.append(
                {
                    "output_type": "error",
                    "ename": o.ename,
                    "evalue": o.evalue,
                    "traceback": list(o.traceback),
                }
            )
    return outs


def _load_mime_bundle(mime: str, blob: str, store: CacheStore) -> dict[str, Any]:
    try:
        data = store.get_blob(blob)
    except KeyError:
        return {mime: ""}
    if mime.startswith("image/") and mime != "image/svg+xml":
        return {mime: base64.b64encode(data).decode("ascii")}
    return {mime: data.decode("utf-8", errors="replace")}


def _last_execution_count(manifest: Manifest) -> int | None:
    """Return the latest ``execute_result`` counter.

    nbformat convention: cells show the final `[N]:` prompt from their last
    expression result. Earlier `display_data` + intermediate `execute_result`
    entries are not what a user would expect to see on the prompt.
    """
    for o in reversed(manifest.outputs):
        if isinstance(o, ExecuteResultOutput) and o.execution_count is not None:
            return o.execution_count
    return None
