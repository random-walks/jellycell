"""Render jellycell notebooks + manifests to HTML (spec §2.6).

Piggybacks on :mod:`nbconvert`'s output helpers, :mod:`markdown_it`,
and :mod:`pygments`. Owns the page shell, navigation, and artifact links.
"""

from __future__ import annotations

from jellycell.render.renderer import Renderer

__all__ = ["Renderer"]
