"""`jellycell view` — serve the live catalogue (requires ``[server]`` extra)."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from jellycell.cli.app import GlobalOptions, app
from jellycell.paths import Project, ProjectNotFoundError

_console = Console()


@app.command("view", help="Serve the live HTML catalogue (requires [server] extra).")
def view(
    ctx: typer.Context,
    project: Path | None = typer.Argument(None, help="Project root."),
    host: str | None = typer.Option(None, "--host", help="Bind host."),
    port: int | None = typer.Option(None, "--port", help="Bind port."),
) -> None:
    """Start a Starlette + SSE server for live preview."""
    opts: GlobalOptions = ctx.obj
    start = project or opts.project_override or Path.cwd()
    try:
        proj = Project.from_path(start)
    except ProjectNotFoundError as exc:
        _fail(opts, str(exc))

    try:
        import uvicorn

        from jellycell.server.app import build_app
    except ImportError as exc:
        _fail(
            opts,
            f"[server] extra not installed: {exc}. Install with `pip install 'jellycell[server]'`.",
        )

    host_ = host or proj.config.viewer.host
    port_ = port or proj.config.viewer.port

    if host_ not in _LOOPBACK_HOSTS and not opts.json_output:
        _console.print(
            f"[yellow bold]warning:[/yellow bold] jellycell view has no authentication. "
            f"Binding to [bold]{host_}[/bold] exposes cached outputs, artifacts, and the "
            f"SSE event stream to anyone on the network. Prefer [bold]127.0.0.1[/bold] "
            f"unless you trust every listener."
        )

    asgi_app = build_app(proj)
    if opts.json_output:
        typer.echo(
            json.dumps(
                {
                    "schema_version": 1,
                    "host": host_,
                    "port": port_,
                    "project": str(proj.root),
                    "url": f"http://{host_}:{port_}/",
                    "loopback": host_ in _LOOPBACK_HOSTS,
                }
            )
        )
    else:
        _console.print(f"[green]serving[/green] {proj.root} at http://{host_}:{port_}/")
    uvicorn.run(asgi_app, host=host_, port=port_, log_level="warning")


_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def _fail(opts: GlobalOptions, msg: str) -> None:
    if opts.json_output:
        typer.echo(json.dumps({"schema_version": 1, "error": msg}))
    else:
        _console.print(f"[red]error:[/red] {msg}")
    raise typer.Exit(1)
