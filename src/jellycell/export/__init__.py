"""Export jellycell notebooks + manifests to other formats (spec §2.6).

Supported formats:

- ``.ipynb`` via :mod:`jellycell.export.ipynb` — Jupyter Notebook with
  cached outputs reattached.
- MyST markdown via :mod:`jellycell.export.myst` — full notebook with
  every cell's outputs inline.
- **Tearsheet** markdown via :mod:`jellycell.export.tearsheet` — a curated
  view intended for ``manuscripts/``: markdown narration + inlined figures
  + JSON summaries, no code source dumps.
"""

from __future__ import annotations

from jellycell.export.ipynb import export_ipynb
from jellycell.export.myst import export_md
from jellycell.export.tearsheet import export_tearsheet

__all__ = ["export_ipynb", "export_md", "export_tearsheet"]
