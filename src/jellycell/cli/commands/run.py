"""`jellycell run` — execute a notebook end-to-end with caching."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from jellycell.cli.app import GlobalOptions, app
from jellycell.paths import Project, ProjectNotFoundError
from jellycell.run import Runner, RunReport

_console = Console()


@app.command("run", help="Execute a notebook end-to-end with caching.")
def run(
    ctx: typer.Context,
    notebook: Path = typer.Argument(..., help="Path to the notebook .py file."),
    force: bool = typer.Option(False, "--force", help="Bypass cache (re-execute all cells)."),
) -> None:
    """Execute every code cell of ``notebook``. Cache hits are restored from the store."""
    opts: GlobalOptions = ctx.obj
    notebook = notebook.resolve()
    try:
        project = Project.from_path(notebook)
    except ProjectNotFoundError as exc:
        _fail(opts, str(exc))

    runner = Runner(project)
    try:
        report = runner.run(notebook, force=force)
    finally:
        runner.close()

    if opts.json_output:
        typer.echo(report.model_dump_json())
    else:
        _print_rich(report)

    if report.status == "error":
        raise typer.Exit(1)


def _print_rich(report: RunReport) -> None:
    table = Table(title=f"Run: {report.notebook}")
    table.add_column("Cell")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("ms", justify="right")
    for cell in report.cell_results:
        color = {
            "ok": "green",
            "cached": "cyan",
            "error": "red",
            "skipped": "dim",
        }.get(cell.status, "white")
        table.add_row(
            cell.cell_id,
            cell.cell_name or "-",
            f"[{color}]{cell.status}[/{color}]",
            str(cell.duration_ms),
        )
    _console.print(table)
    cached = sum(1 for c in report.cell_results if c.status == "cached")
    ran = sum(1 for c in report.cell_results if c.status == "ok")
    _console.print(f"[dim]total {report.total_duration_ms}ms, {cached} cached[/dim]")

    # Mixed cache-hit/miss + in-memory dataflow is the foot-gun that bites
    # users who don't use jc.save/jc.load. Warn if we mixed modes in one run.
    if cached and ran:
        _console.print(
            "[yellow]note:[/yellow] mixed cache/re-execute — "
            f"{cached} cell(s) restored from cache, {ran} re-executed. "
            "If a re-executed cell references in-memory state from a cached "
            "cell, it will fail with [italic]NameError[/italic]. "
            "Use [bold]jc.save[/bold]/[bold]jc.load[/bold] for inter-cell data."
        )

    # Surface error tracebacks inline so users don't need to rerun with --verbose
    # or inspect the manifest by hand.
    for cell in report.cell_results:
        if cell.status == "error" and cell.error is not None:
            _console.print()
            _console.print(
                f"[red bold]{cell.cell_id}[/red bold]"
                f"{f' ({cell.cell_name})' if cell.cell_name else ''}"
                f" [red]{cell.error.ename}[/red]: {cell.error.evalue}"
            )
            if cell.error.traceback:
                _console.print("[dim]" + "\n".join(cell.error.traceback) + "[/dim]")

    # Large-artifact warnings — gitignore or LFS guidance for files likely too
    # big to commit. Threshold is [artifacts] max_committed_size_mb (default 50).
    if report.large_artifacts:
        _console.print()
        limit = report.large_artifacts[0].limit_mb
        _console.print(
            f"[yellow]note:[/yellow] {len(report.large_artifacts)} artifact(s) "
            f"exceed [bold]{limit} MB[/bold] — consider `.gitignore` or Git LFS:"
        )
        for w in report.large_artifacts:
            label = f" ({w.cell_name})" if w.cell_name else ""
            _console.print(
                f"  [dim]{w.cell_id}{label}[/dim] {w.path} [bold]{w.size_mb:.2f} MB[/bold]"
            )


def _fail(opts: GlobalOptions, msg: str) -> None:
    if opts.json_output:
        typer.echo(json.dumps({"schema_version": 1, "error": msg}))
    else:
        _console.print(f"[red]error:[/red] {msg}")
    raise typer.Exit(1)
