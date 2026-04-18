"""Parse and write jellycell notebooks (jupytext percent format + PEP-723).

The flow, per spec §2.2:

1. ``parse`` strips the PEP-723 block, runs :mod:`jupytext` on the remainder,
   then wraps the result in our :class:`~jellycell.format.cells.Notebook` IR.
2. ``write`` re-emits via :mod:`jupytext` and re-inserts the raw PEP-723 block
   verbatim at the top.

Byte-exact round-trip is verified for canonical percent-format inputs. See
``tests/unit/test_format_parse.py``.
"""

from __future__ import annotations

from pathlib import Path

import jupytext
import nbformat

from jellycell.format import pep723
from jellycell.format.cells import Cell, CellSpec, Notebook
from jellycell.format.tags import parse_tags


def parse(path: Path) -> Notebook:
    """Read and parse a jellycell notebook from disk."""
    text = path.read_text(encoding="utf-8")
    return parse_text(text)


def parse_text(text: str) -> Notebook:
    """Parse a jellycell notebook from a string."""
    block, body = pep723.extract(text)
    # Strip leading blank lines so jupytext doesn't synthesize an implicit
    # empty first code cell. We restore the whitespace verbatim on write.
    stripped = body.lstrip()
    leading_whitespace = body[: len(body) - len(stripped)]
    nbnode = jupytext.reads(stripped, fmt="py:percent") if stripped else nbformat.v4.new_notebook()

    cells: list[Cell] = []
    for i, nb_cell in enumerate(nbnode.cells):
        source = nb_cell.source
        if isinstance(source, list):
            source = "".join(source)
        metadata = dict(nb_cell.get("metadata", {}))
        tags = metadata.get("tags", [])
        spec: CellSpec
        if nb_cell.cell_type == "code" and isinstance(tags, list):
            spec = parse_tags(tags)
        else:
            spec = CellSpec()
        cells.append(
            Cell(
                cell_type=nb_cell.cell_type,
                source=source,
                spec=spec,
                metadata=metadata,
                ordinal=i,
            )
        )

    nb_metadata = dict(nbnode.get("metadata", {}))
    if block is not None:
        jellycell_meta = dict(nb_metadata.get("jellycell", {}))
        jellycell_meta["pep723"] = block
        nb_metadata["jellycell"] = jellycell_meta

    return Notebook(
        cells=cells,
        metadata=nb_metadata,
        pep723_block=block,
        leading_whitespace=leading_whitespace,
    )


def write(notebook: Notebook, path: Path) -> None:
    """Write a jellycell notebook to disk."""
    path.write_text(write_text(notebook), encoding="utf-8")


def write_text(notebook: Notebook) -> str:
    """Serialize a :class:`Notebook` to jellycell percent-format text."""
    nb = nbformat.v4.new_notebook()
    # Preserve notebook-level metadata; strip our internal pep723 stash since
    # it lives on :attr:`Notebook.pep723_block` as the source of truth.
    for k, v in notebook.metadata.items():
        if k == "jellycell" and isinstance(v, dict):
            filtered = {sk: sv for sk, sv in v.items() if sk != "pep723"}
            if filtered:
                nb.metadata[k] = filtered
        else:
            nb.metadata[k] = v

    for cell in notebook.cells:
        if cell.cell_type == "code":
            nb_cell = nbformat.v4.new_code_cell(cell.source)
        elif cell.cell_type == "markdown":
            nb_cell = nbformat.v4.new_markdown_cell(cell.source)
        else:
            nb_cell = nbformat.v4.new_raw_cell(cell.source)
        nb_cell.metadata.update(cell.metadata)
        nb.cells.append(nb_cell)

    body = jupytext.writes(nb, fmt="py:percent")
    return pep723.insert(notebook.pep723_block, notebook.leading_whitespace + body)
