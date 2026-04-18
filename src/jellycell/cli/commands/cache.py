"""`jellycell cache` — list, clear, rebuild-index, prune."""

from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import typer
from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

from jellycell.cache.index import CacheIndex
from jellycell.cache.store import CacheStore
from jellycell.cli.app import GlobalOptions, app
from jellycell.paths import Project, ProjectNotFoundError

_console = Console()

cache_app = typer.Typer(
    name="cache",
    help="Inspect and manage the content-addressed cache.",
    no_args_is_help=True,
)
app.add_typer(cache_app, name="cache")


class CacheListReport(BaseModel):
    """JSON schema for ``jellycell cache list --json``. §10.1 contract."""

    schema_version: int = 1
    project: str
    entries: list[dict[str, Any]] = Field(default_factory=list)


class CacheClearReport(BaseModel):
    """JSON schema for ``jellycell cache clear --json``."""

    schema_version: int = 1
    project: str
    removed_manifests: int
    removed_blobs: bool


class CacheRebuildReport(BaseModel):
    """JSON schema for ``jellycell cache rebuild-index --json``."""

    schema_version: int = 1
    project: str
    indexed: int


class CachePruneEntry(BaseModel):
    """One pruned manifest, for the ``cache prune`` JSON report."""

    cache_key: str
    notebook: str
    cell_id: str
    executed_at: str


class CachePruneReport(BaseModel):
    """JSON schema for ``jellycell cache prune --json``."""

    schema_version: int = 1
    project: str
    dry_run: bool
    removed: list[CachePruneEntry] = Field(default_factory=list)
    kept: int = 0


_DURATION_RE = re.compile(r"^(?P<num>\d+)(?P<unit>[smhdw])$")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 86400 * 7}


def _parse_duration(spec: str) -> timedelta:
    """Parse shorthand like ``7d``, ``12h``, ``30m`` into a timedelta."""
    match = _DURATION_RE.match(spec.strip())
    if not match:
        raise ValueError(f"invalid duration {spec!r}; expected e.g. '30d', '12h', '90m', '30s'")
    return timedelta(seconds=int(match.group("num")) * _UNIT_SECONDS[match.group("unit")])


@cache_app.command("list", help="List cached cell executions.")
def list_cache(
    ctx: typer.Context,
    project: Path | None = typer.Argument(None, help="Project root."),
) -> None:
    """List cached cells ordered by most recent first."""
    opts: GlobalOptions = ctx.obj
    proj = _load_project(opts, project)
    index = CacheIndex(proj.cache_dir / "state.db")
    try:
        entries = index.list_all()
    finally:
        index.close()

    report = CacheListReport(project=str(proj.root), entries=entries)

    if opts.json_output:
        typer.echo(report.model_dump_json())
        return
    if not entries:
        _console.print("[dim]cache is empty[/dim]")
        return
    table = Table(title=f"Cache: {proj.root}")
    table.add_column("Key")
    table.add_column("Notebook")
    table.add_column("Cell")
    table.add_column("Status")
    table.add_column("ms", justify="right")
    for row in entries:
        table.add_row(
            str(row["cache_key"])[:12],
            str(row["notebook"]),
            f"{row['cell_id']} ({row['cell_name'] or '-'})",
            str(row["status"]),
            str(row["duration_ms"]),
        )
    _console.print(table)


@cache_app.command("clear", help="Remove all cached manifests and blobs.")
def clear_cache(
    ctx: typer.Context,
    project: Path | None = typer.Argument(None, help="Project root."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation."),
) -> None:
    """Wipe the cache directory. Pass ``--yes`` to skip interactive confirmation."""
    opts: GlobalOptions = ctx.obj
    proj = _load_project(opts, project)
    cache_root = proj.cache_dir
    if not yes and not opts.json_output:
        _console.print(f"This will remove {cache_root}.")
        confirm = typer.confirm("Continue?")
        if not confirm:
            raise typer.Exit()

    removed_manifests = 0
    manifests_dir = cache_root / "manifests"
    if manifests_dir.exists():
        removed_manifests = len(list(manifests_dir.glob("*.json")))
    removed_blobs = cache_root.exists()
    if cache_root.exists():
        shutil.rmtree(cache_root)

    report = CacheClearReport(
        project=str(proj.root),
        removed_manifests=removed_manifests,
        removed_blobs=removed_blobs,
    )
    if opts.json_output:
        typer.echo(report.model_dump_json())
    else:
        _console.print(f"[yellow]cleared[/yellow] {removed_manifests} manifests")


@cache_app.command("prune", help="Remove cached manifests by age or per-notebook count.")
def prune_cache(
    ctx: typer.Context,
    project: Path | None = typer.Argument(None, help="Project root."),
    older_than: str | None = typer.Option(
        None,
        "--older-than",
        help="Remove entries executed more than this duration ago (e.g. '30d', '12h').",
    ),
    keep_last: int | None = typer.Option(
        None,
        "--keep-last",
        help="Keep only the N most recent entries per notebook; drop the rest.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="List what would be removed; don't delete."
    ),
) -> None:
    """Prune old cache entries.

    In this release, prune operates on **manifests only**. Blobs are left in
    place (diskcache dedupes content-addressed storage anyway; a proper
    ref-counted blob GC lands in a follow-up). Use ``cache clear`` for a full
    wipe if you need to reclaim disk.
    """
    opts: GlobalOptions = ctx.obj
    if older_than is None and keep_last is None:
        _console.print("[red]error:[/red] pass at least one of --older-than or --keep-last")
        raise typer.Exit(2)

    proj = _load_project(opts, project)
    index = CacheIndex(proj.cache_dir / "state.db")
    try:
        entries = index.list_all()
    finally:
        index.close()

    to_remove: list[dict[str, Any]] = []
    cutoff: datetime | None = None
    if older_than is not None:
        try:
            cutoff = datetime.now(UTC) - _parse_duration(older_than)
        except ValueError as exc:
            _console.print(f"[red]error:[/red] {exc}")
            raise typer.Exit(2) from exc
        for row in entries:
            if datetime.fromisoformat(str(row["executed_at"])) < cutoff:
                to_remove.append(row)

    if keep_last is not None:
        by_notebook: dict[str, list[dict[str, Any]]] = {}
        for row in entries:
            by_notebook.setdefault(str(row["notebook"]), []).append(row)
        for rows in by_notebook.values():
            rows.sort(key=lambda r: str(r["executed_at"]), reverse=True)
            for extra in rows[keep_last:]:
                if extra not in to_remove:
                    to_remove.append(extra)

    manifests_dir = proj.cache_dir / "manifests"
    for row in to_remove:
        if dry_run:
            continue
        manifest_file = manifests_dir / f"{row['cache_key']}.json"
        if manifest_file.exists():
            manifest_file.unlink()

    # Refresh the SQLite index so it reflects disk truth.
    if not dry_run and to_remove:
        store = CacheStore(proj.cache_dir)
        index = CacheIndex(proj.cache_dir / "state.db")
        try:
            index.rebuild_from_store(store)
        finally:
            index.close()
            store.close()

    report = CachePruneReport(
        project=str(proj.root),
        dry_run=dry_run,
        removed=[
            CachePruneEntry(
                cache_key=str(row["cache_key"]),
                notebook=str(row["notebook"]),
                cell_id=str(row["cell_id"]),
                executed_at=str(row["executed_at"]),
            )
            for row in to_remove
        ],
        kept=len(entries) - len(to_remove),
    )

    if opts.json_output:
        typer.echo(report.model_dump_json())
    else:
        verb = "would remove" if dry_run else "removed"
        _console.print(
            f"[yellow]{verb}[/yellow] {len(to_remove)} manifests; [dim]{report.kept} kept[/dim]"
        )
        if to_remove and not dry_run:
            _console.print("[dim]run `jellycell cache rebuild-index` if blobs need GC later[/dim]")


@cache_app.command("rebuild-index", help="Re-scan manifests to rebuild the SQLite index.")
def rebuild_index(
    ctx: typer.Context,
    project: Path | None = typer.Argument(None, help="Project root."),
) -> None:
    """Rebuild the SQLite catalogue index from the manifest files on disk."""
    opts: GlobalOptions = ctx.obj
    proj = _load_project(opts, project)
    store = CacheStore(proj.cache_dir)
    index = CacheIndex(proj.cache_dir / "state.db")
    try:
        count = index.rebuild_from_store(store)
    finally:
        index.close()
        store.close()
    report = CacheRebuildReport(project=str(proj.root), indexed=count)
    if opts.json_output:
        typer.echo(report.model_dump_json())
    else:
        _console.print(f"[green]indexed[/green] {count} manifests")


def _load_project(opts: GlobalOptions, project: Path | None) -> Project:
    start = project or opts.project_override or Path.cwd()
    try:
        return Project.from_path(start)
    except ProjectNotFoundError as exc:
        if opts.json_output:
            typer.echo(json.dumps({"schema_version": 1, "error": str(exc)}))
        else:
            _console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(1) from exc
