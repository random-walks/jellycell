"""`jellycell export ipynb|md` — export notebooks with reattached outputs."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from pydantic import BaseModel
from rich.console import Console

from jellycell.cache.index import CacheIndex
from jellycell.cache.manifest import Manifest
from jellycell.cache.store import CacheStore
from jellycell.cli.app import GlobalOptions, app
from jellycell.export import export_ipynb, export_md, export_tearsheet
from jellycell.paths import Project, ProjectNotFoundError

_console = Console()

export_app = typer.Typer(
    name="export",
    help="Export notebooks (with cached outputs) to .ipynb, MyST .md, or a curated tearsheet.",
    no_args_is_help=True,
)
app.add_typer(export_app, name="export")


class ExportReport(BaseModel):
    """JSON schema for ``jellycell export --json``. Spec §10.1 contract."""

    schema_version: int = 1
    source: str
    output: str
    format: str


def _load_manifests(project: Project, notebook_rel: str, store: CacheStore) -> dict[str, Manifest]:
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


def _prepare(
    ctx: typer.Context, notebook: Path, suffix: str
) -> tuple[Project, Path, dict[str, Manifest], CacheStore, Path]:
    opts: GlobalOptions = ctx.obj
    source = notebook.resolve()
    try:
        project = Project.from_path(source)
    except ProjectNotFoundError as exc:
        _fail(opts, str(exc))
    notebook_rel = str(source.relative_to(project.root))
    store = CacheStore(project.cache_dir)
    manifests = _load_manifests(project, notebook_rel, store)
    output = project.reports_dir / f"{source.stem}{suffix}"
    output.parent.mkdir(parents=True, exist_ok=True)
    return project, source, manifests, store, output


@export_app.command("ipynb", help="Export to Jupyter Notebook (.ipynb).")
def export_ipynb_cmd(
    ctx: typer.Context,
    notebook: Path = typer.Argument(..., help="Source notebook (.py)."),
) -> None:
    """Write a ``.ipynb`` with cached outputs reattached to ``reports/<stem>.ipynb``."""
    opts: GlobalOptions = ctx.obj
    project, source, manifests, store, output = _prepare(ctx, notebook, ".ipynb")
    try:
        export_ipynb(source, manifests, store, output)
    finally:
        store.close()
    report = ExportReport(
        source=str(source.relative_to(project.root)),
        output=str(output),
        format="ipynb",
    )
    _emit(opts, report)


@export_app.command("md", help="Export to MyST markdown (.md).")
def export_md_cmd(
    ctx: typer.Context,
    notebook: Path = typer.Argument(..., help="Source notebook (.py)."),
) -> None:
    """Write a MyST markdown file with cached outputs to ``reports/<stem>.md``."""
    opts: GlobalOptions = ctx.obj
    project, source, manifests, store, output = _prepare(ctx, notebook, ".md")
    try:
        export_md(source, manifests, store, output)
    finally:
        store.close()
    report = ExportReport(
        source=str(source.relative_to(project.root)),
        output=str(output),
        format="md",
    )
    _emit(opts, report)


@export_app.command(
    "tearsheet",
    help="Curated markdown tearsheet → manuscripts/tearsheets/<stem>.md.",
)
def export_tearsheet_cmd(
    ctx: typer.Context,
    notebook: Path = typer.Argument(..., help="Source notebook (.py)."),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Write to this path instead of the default manuscripts/tearsheets/<stem>.md.",
    ),
) -> None:
    """Write a curated markdown tearsheet.

    Defaults to ``manuscripts/tearsheets/<stem>.md`` so the auto-generated
    subfolder stays separate from the hand-authored writeups that live at
    the root of ``manuscripts/`` (paper drafts, memos, thesis chapters).
    Use ``-o PATH`` to target anywhere else.

    Unlike ``export md``, this skips code source by default and only inlines
    what renders naturally in markdown (figures, JSON summaries, setup cells).
    The result is safe to commit and renders inline on GitHub.
    """
    opts: GlobalOptions = ctx.obj
    opts_obj: GlobalOptions = ctx.obj
    source = notebook.resolve()
    try:
        project = Project.from_path(source)
    except ProjectNotFoundError as exc:
        _fail(opts_obj, str(exc))
    notebook_rel = str(source.relative_to(project.root))
    store = CacheStore(project.cache_dir)
    try:
        manifests = _load_manifests(project, notebook_rel, store)
        default_target = project.manuscripts_dir / "tearsheets" / f"{source.stem}.md"
        target = output.resolve() if output else default_target
        target.parent.mkdir(parents=True, exist_ok=True)
        export_tearsheet(source, manifests, target, project.root)
    finally:
        store.close()
    report = ExportReport(
        source=notebook_rel,
        output=str(target),
        format="tearsheet",
    )
    _emit(opts, report)


def _emit(opts: GlobalOptions, report: ExportReport) -> None:
    if opts.json_output:
        typer.echo(report.model_dump_json())
    else:
        _console.print(f"[green]exported[/green] {report.source} → {report.output}")


def _fail(opts: GlobalOptions, msg: str) -> None:
    if opts.json_output:
        typer.echo(json.dumps({"schema_version": 1, "error": msg}))
    else:
        _console.print(f"[red]error:[/red] {msg}")
    raise typer.Exit(1)
