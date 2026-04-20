"""``jellycell.tearsheets.audit`` — notebook → audit manuscript.

Thin wrapper over :func:`jellycell.export.tearsheet.export_tearsheet`
that pulls manifests from the project's cache for you. Useful when you
want to generate the same per-notebook tearsheet the CLI produces, but
from inside a :py:obj:`jc.step`-tagged cell so the output becomes part
of the cache graph.
"""

from __future__ import annotations

from pathlib import Path

from jellycell.cache.index import CacheIndex
from jellycell.cache.manifest import Manifest
from jellycell.cache.store import CacheStore
from jellycell.export.tearsheet import export_tearsheet
from jellycell.paths import Project

__all__ = ["audit"]


def audit(
    notebook: str | Path,
    *,
    out_path: str | Path,
    template_overrides: dict[str, str] | None = None,
) -> Path:
    """Render a per-notebook tearsheet (cells, artifacts, JSON summaries) as markdown.

    Equivalent to ``jellycell export tearsheet <notebook>`` but callable
    from inside a notebook cell. Reads manifests from the active
    project's cache; a cell that hasn't run yet shows up as
    "(not cached)" in the output.

    Args:
        notebook: Path to the ``.py`` source notebook. Walks up for the
            nearest ``jellycell.toml`` to resolve the project root.
        out_path: Destination markdown file. Parent dirs are created.
        template_overrides: Reserved for header pinning (author,
            month_year, version). Currently unused by the underlying
            exporter — passed along as a no-op for API symmetry with
            :func:`findings` and :func:`methodology`. Future releases
            will flow these into the rendered header.

    Returns:
        The resolved ``Path`` that was written.

    Raises:
        ProjectNotFoundError: No ``jellycell.toml`` was found walking
            up from ``notebook``.
        FileNotFoundError: ``notebook`` does not exist.
    """
    notebook_path = Path(notebook).expanduser().resolve()
    if not notebook_path.exists():
        raise FileNotFoundError(f"notebook not found: {notebook_path}")

    # Project.from_path raises ProjectNotFoundError if no jellycell.toml found.
    project = Project.from_path(notebook_path)

    manifests = _load_manifests(project, str(notebook_path.relative_to(project.root)))
    target = Path(out_path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)

    # template_overrides is currently a pass-through — accepted for API
    # symmetry with findings() and methodology(). A follow-up will flow
    # author/month_year/version into the rendered header.
    _ = template_overrides

    return export_tearsheet(
        notebook_path=notebook_path,
        manifests_by_cell=manifests,
        output_path=target,
        project_root=project.root,
    )


def _load_manifests(project: Project, notebook_rel: str) -> dict[str, Manifest]:
    store = CacheStore(project.cache_dir)
    try:
        idx = CacheIndex(project.cache_dir / "state.db")
        try:
            entries = idx.list_by_notebook(notebook_rel)
        finally:
            idx.close()
        manifests: dict[str, Manifest] = {}
        for row in entries:
            try:
                m = store.get_manifest(row["cache_key"])
            except KeyError:
                continue
            manifests[m.cell_id] = m
        return manifests
    finally:
        store.close()
