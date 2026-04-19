"""The ``jc.*`` API — what notebook cells import (spec §2.4).

Every call has two modes:

- **Inside a run** (``jellycell.run.context.get_context()`` returns a non-None):
  resolves paths relative to the project root, and side effects
  (artifacts, declared deps, caption/notes/tags metadata) are picked up
  by the runner.
- **Standalone** (no run context): falls back to a plain file op, no
  manifest side effect.
"""

from __future__ import annotations

import hashlib
import json
import pickle
import uuid
from pathlib import Path
from typing import Any

from jellycell.run.context import RunContext, get_context


# ---------------------------------------------------------------------- writes
def save(
    obj: Any,
    path: str | Path,
    *,
    format: str | None = None,
    caption: str | None = None,
    notes: str | None = None,
    tags: list[str] | None = None,
) -> Path:
    """Write ``obj`` to ``path``. Format inferred from suffix unless overridden.

    Supported formats: ``parquet``, ``csv``, ``json``, ``pkl``, ``png``.
    Duck-typed — the caller's object must support the corresponding method
    (e.g., ``to_parquet`` for pandas DataFrames).

    ``caption`` / ``notes`` / ``tags`` are optional metadata — inside a run
    they're attached to the produced artifact's :class:`ArtifactRecord` and
    surfaced in tearsheets. Standalone: ignored (no manifest to write to).
    """
    target = _resolve_out(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fmt = format or target.suffix.lstrip(".")
    _write_by_format(obj, target, fmt)
    _record_artifact_metadata(target, caption=caption, notes=notes, tags=tags)
    return target


def figure(
    path: str | Path | None = None,
    *,
    caption: str | None = None,
    notes: str | None = None,
    tags: list[str] | None = None,
    fig: Any = None,
) -> Path:
    """Save a matplotlib figure, or register a pre-rendered image at ``path``.

    Two modes:

    - **Render** — ``fig=`` given, or omitted with ``plt.gcf()`` available:
      the figure is saved to ``path`` (or a sensible default if ``path`` is
      ``None``, honoring ``[artifacts] layout``).
    - **Path-only** — ``fig`` omitted and ``path`` points to an existing image
      file: no matplotlib re-encode. The file is registered as an artifact
      (metadata attached) and displayed inline via IPython. This is the
      idiomatic form for verbatim-mirror analyses where figures are
      pre-rendered on disk.

    ``caption`` / ``notes`` / ``tags`` flow into the artifact's
    :class:`ArtifactRecord` and show up in tearsheets alongside the image.
    """
    ctx = get_context()
    if path is None:
        stem = "figure"
        if ctx is not None and ctx.cell_name:
            stem = ctx.cell_name
        elif ctx is not None:
            stem = ctx.cell_id.replace(":", "_")
        path_ = _layout_path(ctx, stem, "png")
    else:
        path_ = str(path)

    target = _resolve_out(path_)

    # Path-only invocation: the image already exists on disk — register the
    # artifact + display inline, skip the matplotlib re-encode. Only triggers
    # when the caller explicitly passes a path (no auto-default) and didn't
    # provide a fig; otherwise fall through to the render path.
    if fig is None and path is not None and target.is_file():
        # Touch the file so the runner's artifact-diff picks it up. mtime
        # changes don't affect git (content-addressed), and the touch is a
        # no-op if the file is outside the project's artifacts_dir.
        target.touch()
        _record_artifact_metadata(target, caption=caption, notes=notes, tags=tags)
        _inline_display_image(target)
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    if fig is None:
        import matplotlib.pyplot

        fig = matplotlib.pyplot.gcf()
    fig.savefig(target, bbox_inches="tight")
    _record_artifact_metadata(target, caption=caption, notes=notes, tags=tags)
    return target


def _inline_display_image(target: Path) -> None:
    """Best-effort IPython inline display of an image file.

    No-op outside an IPython-compatible context (plain Python, pytest, etc.);
    inside a jellycell run the display_data message is captured by the
    kernel and reattached to the cell on HTML/ipynb export.
    """
    try:
        from IPython.display import Image, display
    except ImportError:
        return
    try:
        display(Image(filename=str(target)))  # type: ignore[no-untyped-call]
    except Exception:
        return


def table(
    df: Any,
    *,
    caption: str | None = None,
    notes: str | None = None,
    tags: list[str] | None = None,
    name: str | None = None,
) -> Path:
    """Save a tabular (pandas DataFrame) to a parquet artifact.

    Like :func:`figure`, the default path honors ``[artifacts] layout`` and
    ``caption`` / ``notes`` / ``tags`` flow into the artifact's manifest record.
    """
    ctx = get_context()
    stem = name or (ctx.cell_name if ctx and ctx.cell_name else "table")
    target = _resolve_out(_layout_path(ctx, stem, "parquet"))
    target.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(target)
    _record_artifact_metadata(target, caption=caption, notes=notes, tags=tags)
    return target


def _record_artifact_metadata(
    target: Path,
    *,
    caption: str | None,
    notes: str | None,
    tags: list[str] | None,
) -> None:
    """Stash caption/notes/tags for the runner to pick up.

    Writes a small JSON into ``<cache_dir>/pending-meta/<uuid>.json`` inside
    a run; no-op in standalone mode. Runner scans the directory after each
    cell execution, enriches the corresponding :class:`ArtifactRecord`, and
    cleans up. The filename is a uuid so two cells producing artifacts at
    the same path in the same run don't step on each other.
    """
    if caption is None and notes is None and not tags:
        return
    ctx = get_context()
    if ctx is None:
        return
    try:
        rel = str(target.resolve().relative_to(ctx.project.root.resolve()))
    except ValueError:
        return
    meta_dir = ctx.project.cache_dir / "pending-meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    # Prefix with a short path-hash so debugging is easier but uniqueness is
    # still guaranteed by the uuid suffix.
    prefix = hashlib.sha256(rel.encode("utf-8")).hexdigest()[:8]
    target_file = meta_dir / f"{prefix}-{uuid.uuid4().hex}.json"
    payload = {
        "path": rel,
        "caption": caption,
        "notes": notes,
        "tags": list(tags) if tags else [],
    }
    target_file.write_text(json.dumps(payload), encoding="utf-8")


def _layout_path(ctx: RunContext | None, stem: str, ext: str) -> str:
    """Pick the default artifact path per ``[artifacts] layout``.

    Standalone (no RunContext): always flat — we don't know notebook/cell
    context. Inside a run: ``flat`` / ``by_notebook`` / ``by_cell``.
    """
    if ctx is None:
        return f"artifacts/{stem}.{ext}"
    artifacts_dir = ctx.project.config.paths.artifacts
    layout = ctx.project.config.artifacts.layout
    notebook_stem = Path(ctx.notebook).stem if ctx.notebook else ""
    cell = ctx.cell_name or ctx.cell_id.replace(":", "_")
    if layout == "by_cell":
        return f"{artifacts_dir}/{notebook_stem}/{cell}/{stem}.{ext}"
    if layout == "by_notebook":
        return f"{artifacts_dir}/{notebook_stem}/{stem}.{ext}"
    return f"{artifacts_dir}/{stem}.{ext}"


# ----------------------------------------------------------------------- reads
def load(path: str | Path) -> Any:
    """Load an object from ``path``. Format inferred from suffix.

    Inside a run, also registers a dep edge on the producing cell (looked up
    via :meth:`CacheIndex.find_producer`) so the caller's cache key
    incorporates the producer's state. Best-effort: if the artifact has no
    recorded producer yet, the load still succeeds without a dep edge.
    """
    src = _resolve_out(path)
    ctx = get_context()
    if ctx is not None:
        _register_producer_dep(ctx, path)
    return _read_by_format(src, src.suffix.lstrip("."))


def path(name: str) -> Path:
    """Resolve a named artifact path.

    If ``name`` matches a known cell's name (via the artifact lineage index),
    returns the path of the artifact that cell produced. Otherwise falls back
    to ``<artifacts>/<name>``.
    """
    ctx = get_context()
    if ctx is None:
        return Path("artifacts") / name
    # Try to resolve by producer cell name via the cache index.
    try:
        from jellycell.cache.index import CacheIndex

        with CacheIndex(ctx.project.cache_dir / "state.db") as idx:
            producer = _find_by_cell_name(idx, name, ctx.notebook)
    except Exception:
        producer = None
    if producer:
        return ctx.project.root / producer
    return ctx.project.artifacts_dir / name


def _register_producer_dep(ctx: RunContext, artifact_path: str | Path) -> None:
    """Best-effort: add the producing cell's name to ``ctx.declared_deps``.

    No-op on any exception — dep tracking is an enhancement, not a requirement
    for the load to succeed.
    """
    try:
        from jellycell.cache.index import CacheIndex
    except Exception:
        return

    rel = str(artifact_path)
    if Path(rel).is_absolute():
        try:
            rel = str(Path(rel).resolve().relative_to(ctx.project.root.resolve()))
        except ValueError:
            return

    try:
        with CacheIndex(ctx.project.cache_dir / "state.db") as idx:
            producer = idx.find_producer(rel)
    except Exception:
        return
    if not producer:
        return
    name = producer.get("cell_name")
    if name and name not in ctx.declared_deps:
        ctx.declared_deps.append(name)


def _find_by_cell_name(index: object, cell_name: str, notebook: str) -> str | None:
    """Return the artifact path produced by ``cell_name`` in ``notebook``, if any."""
    try:
        cur = index._conn.execute(  # type: ignore[attr-defined]
            "SELECT a.path FROM artifacts a "
            "JOIN cells c ON a.producer_cache_key = c.cache_key "
            "WHERE c.cell_name = ? AND c.notebook = ? "
            "ORDER BY c.executed_at DESC LIMIT 1",
            (cell_name, notebook),
        )
        row = cur.fetchone()
    except Exception:
        return None
    return row[0] if row else None


def deps(*names: str) -> None:
    """Declare explicit deps for this cell (spec §2.4).

    At runtime this is a no-op — the runner AST-walks cell source statically
    to find these calls before execution (spec §2.5). Runtime tracking is kept
    as a fallback for dynamic cases.
    """
    ctx = get_context()
    if ctx is not None:
        for n in names:
            if n not in ctx.declared_deps:
                ctx.declared_deps.append(n)


def cache(fn: Any) -> Any:
    """Memoize an expensive function via the cache store (spec §2.4).

    Inside a run: keys on ``(qualname, normalized source, pickled args)`` and
    persists the pickled return value alongside cell outputs.

    Standalone (no RunContext): identity passthrough — no caching.
    """
    from jellycell.cache.function_cache import cache_function

    return cache_function(fn)


# ----------------------------------------------------------------------- ctx
class _Ctx:
    """Read-only accessor for the current :class:`RunContext`."""

    @property
    def notebook(self) -> str | None:
        c = get_context()
        return c.notebook if c else None

    @property
    def cell_id(self) -> str | None:
        c = get_context()
        return c.cell_id if c else None

    @property
    def cell_name(self) -> str | None:
        c = get_context()
        return c.cell_name if c else None

    @property
    def project(self) -> Any:
        c = get_context()
        return c.project if c else None

    @property
    def inside_run(self) -> bool:
        """True iff there's an active :class:`RunContext`."""
        return get_context() is not None


ctx = _Ctx()
"""Singleton for ``jc.ctx`` access from cell code."""


# ----------------------------------------------------------------------- impl
def _resolve_out(path: str | Path) -> Path:
    """Resolve ``path`` against project root when inside a run, else CWD."""
    p = Path(path)
    ctx = get_context()
    if ctx is None:
        return p.resolve() if p.is_absolute() else (Path.cwd() / p).resolve()
    if p.is_absolute():
        raise ValueError("Absolute paths are not permitted inside a run.")
    return ctx.project.resolve(p)


def _write_by_format(obj: Any, target: Path, fmt: str) -> None:
    """Dispatch a write based on the file extension/format."""
    if fmt == "parquet":
        obj.to_parquet(target)
    elif fmt == "csv":
        obj.to_csv(target, index=False)
    elif fmt == "json":
        if hasattr(obj, "model_dump"):
            target.write_text(obj.model_dump_json(indent=2), encoding="utf-8")
        else:
            target.write_text(json.dumps(obj, default=str, indent=2), encoding="utf-8")
    elif fmt in ("pkl", "pickle"):
        target.write_bytes(pickle.dumps(obj))
    elif fmt == "png":
        obj.savefig(target, bbox_inches="tight")
    else:
        raise ValueError(f"Unsupported format for jc.save: {fmt!r}")


def _read_by_format(src: Path, fmt: str) -> Any:
    """Dispatch a read based on the file extension/format."""
    if fmt == "parquet":
        import pandas as pd

        return pd.read_parquet(src)
    if fmt == "csv":
        import pandas as pd

        return pd.read_csv(src)
    if fmt == "json":
        return json.loads(src.read_text(encoding="utf-8"))
    if fmt in ("pkl", "pickle"):
        return pickle.loads(src.read_bytes())
    raise ValueError(f"Unsupported format for jc.load: {fmt!r}")


__all__ = [
    "cache",
    "ctx",
    "deps",
    "figure",
    "load",
    "path",
    "save",
    "table",
]
