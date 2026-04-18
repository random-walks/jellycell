"""`jellycell checkpoint` — reproducible project snapshots.

Bundles a self-contained ``.tar.gz`` of the project (notebooks, data,
artifacts, reports, manuscripts, ``jellycell.toml``, and the
content-addressed cache) so a reviewer can unpack it and see the
last-run outputs without re-executing anything. Restores land in a
**new sibling directory by default** to avoid any chance of clobbering
in-flight work.

Scope carefully chosen:

- Whitelist which directories go in. Anything else (virtualenvs, pip
  caches, ``.git``, editor scratch) is never archived.
- Include ``.jellycell/cache/`` so artifacts can be rebuilt locally
  from cache hits even without re-running the notebook.
- Skip a small hardcoded set of junk dirs that always appear
  (``__pycache__``, ``.ruff_cache``, ``.mypy_cache``, etc.).
- No gitignore handling for v1 — use ``jellycell cache clear`` first
  if you want lean checkpoints.
"""

from __future__ import annotations

import json
import re
import shutil
import tarfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer
from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

from jellycell.cli.app import GlobalOptions, app
from jellycell.paths import Project, ProjectNotFoundError

_console = Console()

checkpoint_app = typer.Typer(
    name="checkpoint",
    help="Bundle reproducible project snapshots (.tar.gz).",
    no_args_is_help=True,
)
app.add_typer(checkpoint_app, name="checkpoint")


#: Directories we archive. Anything under the project root that isn't one
#: of these (or the top-level ``jellycell.toml``) is ignored.
_INCLUDED_TOP_LEVEL = (
    "notebooks",
    "data",
    "artifacts",
    "site",
    "manuscripts",
    ".jellycell",
)

#: Junk directories we unconditionally skip anywhere in the tree.
_SKIP_DIR_NAMES = frozenset(
    {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".ipynb_checkpoints",
        ".git",
        ".venv",
        "venv",
        "node_modules",
    }
)

_NAME_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


class CheckpointSummary(BaseModel):
    """Metadata embedded in the tarball as ``checkpoint.json``."""

    schema_version: int = 1
    created_at: str
    project_name: str
    message: str | None = None
    files: int
    size_bytes: int


class CheckpointCreateReport(BaseModel):
    """JSON schema for ``jellycell checkpoint create --json``. §10.1 contract."""

    schema_version: int = 1
    project: str
    path: str
    files: int
    size_bytes: int
    message: str | None = None


class CheckpointListEntry(BaseModel):
    """One row in ``checkpoint list``."""

    name: str
    path: str
    created_at: str
    message: str | None = None
    size_bytes: int


class CheckpointListReport(BaseModel):
    """JSON schema for ``jellycell checkpoint list --json``. §10.1 contract."""

    schema_version: int = 1
    project: str
    checkpoints: list[CheckpointListEntry] = Field(default_factory=list)


class CheckpointRestoreReport(BaseModel):
    """JSON schema for ``jellycell checkpoint restore --json``. §10.1 contract."""

    schema_version: int = 1
    project: str
    source: str
    target: str


@checkpoint_app.command("create", help="Bundle the current project into a .tar.gz.")
def checkpoint_create(
    ctx: typer.Context,
    project: Path | None = typer.Argument(None, help="Project root."),
    message: str | None = typer.Option(
        None, "--message", "-m", help="Short label for this checkpoint."
    ),
    name: str | None = typer.Option(
        None, "--name", help="Override the auto-generated checkpoint name."
    ),
) -> None:
    """Write ``.jellycell/checkpoints/<name>.tar.gz``."""
    opts: GlobalOptions = ctx.obj
    proj = _load_project(opts, project)

    now = datetime.now(UTC)
    stem = _safe_name(name or now.strftime("%Y-%m-%dT%H-%M-%SZ"))
    out_dir = proj.cache_dir.parent / "checkpoints"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{stem}.tar.gz"
    if target.exists():
        _fail(opts, f"{target} already exists — pass --name to choose a different one.")

    files = _archive_project(proj, target, now=now, message=message)

    summary = CheckpointSummary(
        created_at=now.isoformat(timespec="seconds"),
        project_name=proj.config.project.name,
        message=message,
        files=files,
        size_bytes=target.stat().st_size,
    )
    # Keep a sidecar alongside the tarball so `list` doesn't need to open
    # every archive just to show metadata. Path.with_suffix only replaces the
    # LAST suffix, so "foo.tar.gz" → "foo.tar.json"; build it explicitly.
    sidecar_path = _sidecar_for(target)
    sidecar_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")

    report = CheckpointCreateReport(
        project=str(proj.root),
        path=str(target),
        files=files,
        size_bytes=summary.size_bytes,
        message=message,
    )
    if opts.json_output:
        typer.echo(report.model_dump_json())
    else:
        _console.print(
            f"[green]checkpoint[/green] {stem} → {target}  "
            f"[dim]({files} files, {_humanize_bytes(summary.size_bytes)})[/dim]"
        )
        if message:
            _console.print(f"  [dim]message:[/dim] {message}")


@checkpoint_app.command("list", help="List existing checkpoints, newest first.")
def checkpoint_list(
    ctx: typer.Context,
    project: Path | None = typer.Argument(None, help="Project root."),
) -> None:
    """Show all checkpoints under ``.jellycell/checkpoints/``."""
    opts: GlobalOptions = ctx.obj
    proj = _load_project(opts, project)
    entries = _collect_entries(proj)

    report = CheckpointListReport(project=str(proj.root), checkpoints=entries)
    if opts.json_output:
        typer.echo(report.model_dump_json())
        return
    if not entries:
        _console.print("[dim]no checkpoints yet[/dim]")
        return
    table = Table(title=f"Checkpoints: {proj.root}")
    table.add_column("Name")
    table.add_column("Created")
    table.add_column("Size", justify="right")
    table.add_column("Message")
    for e in entries:
        table.add_row(e.name, e.created_at, _humanize_bytes(e.size_bytes), e.message or "")
    _console.print(table)


@checkpoint_app.command(
    "restore",
    help="Extract a checkpoint into a new directory (never overwrites in place).",
)
def checkpoint_restore(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Checkpoint name (without .tar.gz)."),
    project: Path | None = typer.Option(
        None, "--project", help="Project root the checkpoint belongs to."
    ),
    into: Path | None = typer.Option(
        None,
        "--into",
        help="Target directory. Defaults to <project>-restored-<name>/ as a sibling.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Allow extraction into an existing, non-empty directory (merges / overwrites).",
    ),
) -> None:
    """Extract ``.jellycell/checkpoints/<name>.tar.gz`` to a target dir."""
    opts: GlobalOptions = ctx.obj
    # Support both the positional `project` of other commands and --project here.
    proj = _load_project(opts, project)
    source = proj.cache_dir.parent / "checkpoints" / f"{name}.tar.gz"
    if not source.exists():
        _fail(opts, f"checkpoint not found: {source}")

    target = _resolve_restore_target(proj.root, into=into, name=name)
    if target.exists() and any(target.iterdir()) and not force:
        _fail(
            opts,
            f"target {target} exists and is non-empty. "
            "Pass --force to merge into it, or --into PATH to pick a fresh location.",
        )
    target.mkdir(parents=True, exist_ok=True)

    with tarfile.open(source, "r:gz") as tar:
        tar.extractall(target, filter="data")

    report = CheckpointRestoreReport(
        project=str(proj.root),
        source=str(source),
        target=str(target),
    )
    if opts.json_output:
        typer.echo(report.model_dump_json())
    else:
        _console.print(f"[green]restored[/green] {name} → {target}")


# ----------------------------------------------------------------- helpers


def _load_project(opts: GlobalOptions, project: Path | None) -> Project:
    start = project or opts.project_override or Path.cwd()
    try:
        return Project.from_path(start)
    except ProjectNotFoundError as exc:
        _fail(opts, str(exc))
    raise AssertionError("unreachable")  # for mypy


def _safe_name(name: str) -> str:
    cleaned = _NAME_SAFE.sub("-", name).strip("-")
    return cleaned or "checkpoint"


def _resolve_restore_target(project_root: Path, *, into: Path | None, name: str) -> Path:
    if into is not None:
        return into.expanduser().resolve()
    # Safe default: sibling directory so the current project is never touched.
    return (project_root.parent / f"{project_root.name}-restored-{_safe_name(name)}").resolve()


def _archive_project(
    project: Project,
    target: Path,
    *,
    now: datetime,
    message: str | None,
) -> int:
    """Write the archive; return the number of files added (excluding
    the embedded ``checkpoint.json`` metadata sidecar)."""
    count = 0
    root = project.root
    with tarfile.open(target, "w:gz") as tar:
        # Project config always makes it in.
        config_path = root / "jellycell.toml"
        if config_path.exists():
            tar.add(config_path, arcname="jellycell.toml")
            count += 1
        for top in _INCLUDED_TOP_LEVEL:
            d = root / top
            if not d.exists():
                continue
            for file in _walk_files(d):
                arcname = str(file.relative_to(root))
                tar.add(file, arcname=arcname)
                count += 1
        # Metadata sidecar so `restore` and future readers can inspect the
        # tarball without separately loading a .json alongside.
        meta = {
            "schema_version": 1,
            "created_at": now.isoformat(timespec="seconds"),
            "project_name": project.config.project.name,
            "message": message,
            "files": count,
        }
        meta_bytes = json.dumps(meta, indent=2).encode("utf-8")
        _add_bytes(tar, "checkpoint.json", meta_bytes, mtime=now.timestamp())
    return count


def _walk_files(root: Path) -> Iterator[Path]:
    """Depth-first walk yielding files under ``root``, skipping junk dirs."""
    for entry in sorted(root.iterdir()):
        if entry.is_dir():
            if entry.name in _SKIP_DIR_NAMES:
                continue
            yield from _walk_files(entry)
        elif entry.is_file() and entry.name not in {".DS_Store"}:
            yield entry


def _add_bytes(tar: tarfile.TarFile, arcname: str, data: bytes, *, mtime: float) -> None:
    import io

    info = tarfile.TarInfo(name=arcname)
    info.size = len(data)
    info.mtime = int(mtime)
    tar.addfile(info, io.BytesIO(data))


def _sidecar_for(tar_path: Path) -> Path:
    """Sidecar metadata path for a ``.tar.gz`` checkpoint.

    ``Path.with_suffix`` only replaces the last extension, so ``foo.tar.gz``
    becomes ``foo.tar.json`` — almost certainly not what we want. Strip the
    double-extension stem manually.
    """
    stem = tar_path.name.removesuffix(".tar.gz")
    return tar_path.parent / f"{stem}.json"


def _collect_entries(project: Project) -> list[CheckpointListEntry]:
    """Read sidecar metadata for every ``*.tar.gz`` under the checkpoints dir."""
    dir_ = project.cache_dir.parent / "checkpoints"
    if not dir_.exists():
        return []
    entries: list[CheckpointListEntry] = []
    for tar in sorted(dir_.glob("*.tar.gz"), reverse=True):
        sidecar = _sidecar_for(tar)
        meta: dict[str, Any] = {}
        if sidecar.exists():
            try:
                meta = json.loads(sidecar.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                meta = {}
        entries.append(
            CheckpointListEntry(
                name=tar.name.removesuffix(".tar.gz"),
                path=str(tar),
                created_at=str(meta.get("created_at", "")),
                message=meta.get("message"),
                size_bytes=tar.stat().st_size,
            )
        )
    return entries


def _humanize_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    if n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    return f"{n / (1024 * 1024 * 1024):.2f} GB"


def _fail(opts: GlobalOptions, msg: str) -> None:
    if opts.json_output:
        typer.echo(json.dumps({"schema_version": 1, "error": msg}))
    else:
        _console.print(f"[red]error:[/red] {msg}")
    raise typer.Exit(1)


# `shutil` imported for future "prune-by-age" support; silence unused import.
_ = shutil
