"""Render cell outputs (from manifests) to safe HTML.

Handles the four ``OutputRecord`` variants. For binary data (images),
either base64-inlines (``inline=True``) or writes blobs to an assets dir
and references them via relative URLs.
"""

from __future__ import annotations

import base64
import html as html_std
from pathlib import Path

from jellycell.cache.manifest import (
    DisplayDataOutput,
    ErrorOutput,
    ExecuteResultOutput,
    OutputRecord,
    StreamOutput,
)
from jellycell.cache.store import CacheStore

#: MIME types we can render inline without further processing.
_TEXT_MIMES = {"text/plain", "text/html", "text/markdown"}


def render_output(
    output: OutputRecord,
    *,
    store: CacheStore,
    assets_dir: Path,
    inline: bool,
) -> str:
    """Render a single output record to an HTML fragment."""
    if isinstance(output, StreamOutput):
        return _render_stream(output, store)
    if isinstance(output, DisplayDataOutput | ExecuteResultOutput):
        return _render_data(output, store=store, assets_dir=assets_dir, inline=inline)
    if isinstance(output, ErrorOutput):
        return _render_error(output)
    return ""  # pragma: no cover — exhaustive above


def _render_stream(output: StreamOutput, store: CacheStore) -> str:
    try:
        data = store.get_blob(output.blob).decode("utf-8", errors="replace")
    except KeyError:
        data = "(blob missing)"
    cls = "jc-stream jc-stderr" if output.name == "stderr" else "jc-stream jc-stdout"
    return f'<pre class="{cls}">{html_std.escape(data)}</pre>'


def _render_data(
    output: DisplayDataOutput | ExecuteResultOutput,
    *,
    store: CacheStore,
    assets_dir: Path,
    inline: bool,
) -> str:
    mime = output.mime
    try:
        data = store.get_blob(output.blob)
    except KeyError:
        return '<div class="jc-output-missing">(blob missing)</div>'

    if mime == "text/plain":
        return f'<pre class="jc-text-plain">{html_std.escape(data.decode("utf-8", errors="replace"))}</pre>'
    if mime == "text/html":
        return f'<div class="jc-html">{data.decode("utf-8", errors="replace")}</div>'
    if mime == "text/markdown":
        from jellycell.render.markdown import render_markdown

        return f'<div class="jc-markdown">{render_markdown(data.decode("utf-8", errors="replace"))}</div>'
    if mime.startswith("image/"):
        return _render_image(mime, data, blob=output.blob, assets_dir=assets_dir, inline=inline)
    if mime == "application/json":
        text = data.decode("utf-8", errors="replace")
        return f'<pre class="jc-json">{html_std.escape(text)}</pre>'
    # Unknown mime — drop in a <pre> with the mime label.
    return (
        f'<div class="jc-unknown-mime">'
        f'<span class="jc-mime">{html_std.escape(mime)}</span>'
        f"<pre>{html_std.escape(data[:1000].decode('utf-8', errors='replace'))}</pre>"
        f"</div>"
    )


def _render_image(mime: str, data: bytes, *, blob: str, assets_dir: Path, inline: bool) -> str:
    ext = {"image/png": "png", "image/jpeg": "jpg", "image/svg+xml": "svg"}.get(mime, "bin")
    if inline:
        if mime == "image/svg+xml":
            return f'<div class="jc-image">{data.decode("utf-8", errors="replace")}</div>'
        b64 = base64.b64encode(data).decode("ascii")
        return f'<img class="jc-image" src="data:{mime};base64,{b64}" alt="" />'
    assets_dir.mkdir(parents=True, exist_ok=True)
    asset_path = assets_dir / f"{blob[:16]}.{ext}"
    if not asset_path.exists():
        asset_path.write_bytes(data)
    return f'<img class="jc-image" src="_assets/{asset_path.name}" alt="" />'


def _render_error(output: ErrorOutput) -> str:
    tb = "\n".join(output.traceback)
    return (
        '<div class="jc-error">'
        f'<div class="jc-error-head">{html_std.escape(output.ename)}: '
        f"{html_std.escape(output.evalue)}</div>"
        f'<pre class="jc-error-tb">{html_std.escape(tb)}</pre>'
        "</div>"
    )


__all__ = ["render_output"]
