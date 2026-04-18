"""`jellycell render` — generate HTML reports for notebooks."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from pydantic import BaseModel, Field
from rich.console import Console

from jellycell.cli.app import GlobalOptions, app
from jellycell.paths import Project, ProjectNotFoundError
from jellycell.render import Renderer

_console = Console()


class RenderedEntry(BaseModel):
    """One rendered notebook entry."""

    notebook: str
    output_path: str
    cell_count: int
    cached_count: int


class RenderReport(BaseModel):
    """JSON schema for ``jellycell render --json``. Spec §10.1 contract."""

    schema_version: int = 1
    project: str
    index: str | None = None
    entries: list[RenderedEntry] = Field(default_factory=list)


@app.command("render", help="Render notebooks to HTML under reports/.")
def render(
    ctx: typer.Context,
    notebook: Path | None = typer.Argument(
        None, help="Notebook to render. Omit to render the whole project + index."
    ),
    standalone: bool = typer.Option(
        False,
        "--standalone",
        help="Base64-inline image assets for a self-contained HTML file.",
    ),
) -> None:
    """Generate HTML reports from cached manifests."""
    opts: GlobalOptions = ctx.obj
    start = notebook.resolve() if notebook else (opts.project_override or Path.cwd())
    try:
        project = Project.from_path(start)
    except ProjectNotFoundError as exc:
        _fail(opts, str(exc))

    renderer = Renderer(project, standalone=standalone)
    try:
        if notebook is not None:
            result = renderer.render_notebook(notebook.resolve())
            entries = [
                RenderedEntry(
                    notebook=result.notebook,
                    output_path=str(result.output_path),
                    cell_count=result.cell_count,
                    cached_count=result.cached_count,
                )
            ]
            index_path = None
        else:
            results = renderer.render_all()
            entries = [
                RenderedEntry(
                    notebook=r.notebook,
                    output_path=str(r.output_path),
                    cell_count=r.cell_count,
                    cached_count=r.cached_count,
                )
                for r in results
            ]
            index_path = str(project.reports_dir / "index.html")
    finally:
        renderer.close()

    report = RenderReport(
        project=str(project.root),
        index=index_path,
        entries=entries,
    )

    if opts.json_output:
        typer.echo(report.model_dump_json())
    else:
        for entry in entries:
            _console.print(
                f"[green]rendered[/green] {entry.notebook} "
                f"[dim]→ {entry.output_path} "
                f"({entry.cached_count}/{entry.cell_count} cached)[/dim]"
            )
        if index_path:
            _console.print(f"[cyan]index[/cyan] {index_path}")


def _fail(opts: GlobalOptions, msg: str) -> None:
    if opts.json_output:
        typer.echo(json.dumps({"schema_version": 1, "error": msg}))
    else:
        _console.print(f"[red]error:[/red] {msg}")
    raise typer.Exit(1)
