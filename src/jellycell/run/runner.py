"""The :class:`Runner` — orchestrates per-cell execution, caching, manifests.

Spec §2.5 / §3:

- Parse notebook (format.parse).
- Iterate cells in source order.
- For each cell, compute a cache key from source + declared deps + env_hash.
- Cache hit → load manifest, skip execution.
- Cache miss → execute via :class:`~jellycell.run.kernel.Kernel`, capture
  outputs, diff the artifacts dir for new files, build manifest, store.

The runner installs a small setup prelude before each cell so ``jc.*`` inside
the kernel sees a live :class:`~jellycell.run.context.RunContext`.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from jellycell.cache import hashing
from jellycell.cache.index import CacheIndex
from jellycell.cache.manifest import (
    ArtifactRecord,
    DisplayDataOutput,
    ErrorOutput,
    ExecuteResultOutput,
    Manifest,
    OutputRecord,
    StreamOutput,
)
from jellycell.cache.store import CacheStore
from jellycell.format import parse as format_parse
from jellycell.format import pep723, static_deps
from jellycell.format.cells import Cell, Notebook
from jellycell.format.pep723 import parse_content as pep723_parse
from jellycell.paths import Project
from jellycell.run.env_hash import compute_env_hash
from jellycell.run.kernel import CellExecution, Kernel
from jellycell.run.pool import KernelPool


class CellError(BaseModel):
    """Structured error details surfaced on a failed ``CellResult``."""

    ename: str
    evalue: str
    traceback: list[str] = Field(default_factory=list)


class CellResult(BaseModel):
    """Per-cell outcome for the run report."""

    cell_id: str
    cell_name: str | None
    status: Literal["ok", "error", "cached", "skipped"]
    cache_key: str | None
    duration_ms: int
    error: CellError | None = None
    """Populated when ``status == "error"``. Optional, additive field (§10.1 safe)."""


class LargeArtifactWarning(BaseModel):
    """One artifact that exceeded ``[artifacts] max_committed_size_mb``."""

    path: str
    size_mb: float
    limit_mb: int
    cell_id: str
    cell_name: str | None = None


class RunReport(BaseModel):
    """JSON schema for ``jellycell run --json``. Spec §10.1 contract."""

    schema_version: int = 1
    notebook: str
    cell_results: list[CellResult] = Field(default_factory=list)
    total_duration_ms: int = 0
    status: Literal["ok", "error"] = "ok"
    large_artifacts: list[LargeArtifactWarning] = Field(default_factory=list)
    """Per-run soft warnings — artifacts above ``max_committed_size_mb``.

    Additive, optional field (§10.1 safe). Consumers that ignore it keep
    working unchanged.
    """


class Runner:
    """Executes a jellycell notebook through a subprocess kernel, with caching.

    Pass ``kernel_pool`` to reuse a kernel across multiple runs (see
    :class:`jellycell.run.pool.KernelPool`). Default is a fresh kernel per
    run for isolation.
    """

    def __init__(self, project: Project, *, kernel_pool: KernelPool | None = None) -> None:
        self.project = project
        project.cache_dir.mkdir(parents=True, exist_ok=True)
        self.store = CacheStore(project.cache_dir)
        self.index = CacheIndex(project.cache_dir / "state.db")
        self._kernel_pool = kernel_pool

    def run(
        self, notebook_path: Path, *, force: bool = False, kernel_name: str | None = None
    ) -> RunReport:
        """Execute all cells in ``notebook_path``. Returns a :class:`RunReport`."""
        notebook = format_parse(notebook_path)
        notebook_rel = str(notebook_path.relative_to(self.project.root))
        env_hash = compute_env_hash(self.project, notebook)

        # Apply PEP-723 [tool.jellycell] file-scope overrides to `project` for
        # this run only. Doesn't mutate `self.project`.
        overrides = pep723.jellycell_overrides(notebook.pep723_block)
        effective = self.project.with_overrides(overrides) if overrides else self.project

        if self._kernel_pool is not None:
            kernel = self._kernel_pool.acquire()
            owns_kernel = False
        else:
            kernel = Kernel(kernel_name=kernel_name or effective.config.run.kernel)
            owns_kernel = True

        report = RunReport(notebook=notebook_rel)
        name_to_key: dict[str, str] = {}

        start = time.perf_counter()
        try:
            if owns_kernel:
                kernel.start()
            for ordinal, cell in enumerate(notebook.cells):
                if cell.cell_type != "code" or cell.spec.kind == "note":
                    continue
                result = self._run_one_cell(
                    kernel=kernel,
                    project=effective,
                    notebook_rel=notebook_rel,
                    cell=cell,
                    ordinal=ordinal,
                    env_hash=env_hash,
                    name_to_key=name_to_key,
                    force=force,
                )
                report.cell_results.append(result)
                if result.cache_key is not None:
                    name = cell.spec.name or f"{_stem(notebook_rel)}:{ordinal}"
                    name_to_key[name] = result.cache_key
                    report.large_artifacts.extend(
                        self._collect_large_artifact_warnings(
                            cache_key=result.cache_key,
                            cell_id=result.cell_id,
                            cell_name=result.cell_name,
                            limit_mb=effective.config.artifacts.max_committed_size_mb,
                        )
                    )
                if result.status == "error":
                    report.status = "error"
                    break
        finally:
            if owns_kernel:
                kernel.stop()
        report.total_duration_ms = int((time.perf_counter() - start) * 1000)
        return report

    def _collect_large_artifact_warnings(
        self,
        *,
        cache_key: str,
        cell_id: str,
        cell_name: str | None,
        limit_mb: int,
    ) -> list[LargeArtifactWarning]:
        """Check this cell's manifest for artifacts larger than ``limit_mb``.

        ``limit_mb = 0`` disables the check. Missing manifest is a no-op so
        cache hits for entries that were pruned don't crash the run.
        """
        if limit_mb <= 0:
            return []
        try:
            manifest = self.store.get_manifest(cache_key)
        except KeyError:
            return []
        threshold = limit_mb * 1024 * 1024
        return [
            LargeArtifactWarning(
                path=art.path,
                size_mb=round(art.size / (1024 * 1024), 2),
                limit_mb=limit_mb,
                cell_id=cell_id,
                cell_name=cell_name,
            )
            for art in manifest.artifacts
            if art.size > threshold
        ]

    # --------------------------------------------------------- cell execution
    def _run_one_cell(
        self,
        *,
        kernel: Kernel,
        project: Project,
        notebook_rel: str,
        cell: Cell,
        ordinal: int,
        env_hash: str,
        name_to_key: dict[str, str],
        force: bool,
    ) -> CellResult:
        cell_name = cell.spec.name
        cell_id = f"{_stem(notebook_rel)}:{ordinal}"

        # Merge tag-declared deps + AST-walked jc.deps(...) + resolved jc.load(...).
        # Static analysis catches the cases the runtime declared_deps can't
        # (because ctx.declared_deps is populated after cache_key is computed).
        declared = list(cell.spec.deps)
        for static_dep in static_deps.extract_static_deps(cell.source):
            if static_dep not in declared:
                declared.append(static_dep)
        for loaded_path in static_deps.extract_loaded_paths(cell.source):
            producer = self.index.find_producer(loaded_path)
            if producer and producer.get("cell_name") and producer["cell_name"] not in declared:
                declared.append(producer["cell_name"])

        dep_keys = [name_to_key[d] for d in declared if d in name_to_key]
        cache_key = hashing.key(source=cell.source, dep_keys=dep_keys, env_hash=env_hash)

        if not force and self.store.has(cache_key):
            manifest = self.store.get_manifest(cache_key)
            # Only `ok` manifests are cache hits. Error manifests get replayed
            # so transient failures retry automatically.
            if manifest.status == "ok":
                return CellResult(
                    cell_id=cell_id,
                    cell_name=cell_name,
                    status="cached",
                    cache_key=cache_key,
                    duration_ms=manifest.duration_ms,
                )

        # Per-cell timeout: tag `timeout=N` wins; otherwise project/override config.
        timeout_s = (
            float(cell.spec.timeout_s)
            if cell.spec.timeout_s is not None
            else float(project.config.run.timeout_seconds)
        )

        prelude = _setup_prelude(project, notebook_rel, cell_id, cell_name)
        before = _snapshot_artifacts(project.artifacts_dir)
        _clear_pending_meta(project.cache_dir)
        t0 = time.perf_counter()
        _ = kernel.execute(prelude)
        execution = kernel.execute(cell.source, timeout=timeout_s)
        duration_ms = int((time.perf_counter() - t0) * 1000)
        after = _snapshot_artifacts(project.artifacts_dir)
        artifacts = _artifacts_diff(project.root, before, after)
        _apply_pending_meta(project.cache_dir, artifacts)

        outputs = _translate_outputs(self.store, execution)
        manifest = Manifest(
            cache_key=cache_key,
            notebook=notebook_rel,
            cell_id=cell_id,
            cell_name=cell_name,
            source_hash=hashing.source_hash(cell.source),
            dep_keys=dep_keys,
            env_hash=env_hash,
            executed_at=datetime.now(UTC),
            duration_ms=duration_ms,
            status="ok" if execution.status == "ok" else "error",
            outputs=outputs,
            artifacts=artifacts,
        )
        manifest_path = self.store.put_manifest(manifest)
        self.index.insert(manifest, manifest_path)

        error: CellError | None = None
        if execution.status == "error":
            error = _extract_error(execution)

        return CellResult(
            cell_id=cell_id,
            cell_name=cell_name,
            status="ok" if execution.status == "ok" else "error",
            cache_key=cache_key,
            duration_ms=duration_ms,
            error=error,
        )

    def close(self) -> None:
        """Close underlying resources."""
        self.store.close()
        self.index.close()


# ------------------------------------------------------------ helper functions


def _extract_error(execution: CellExecution) -> CellError | None:
    """Pull the first error output out of a CellExecution (runner → CLI pipeline)."""
    for raw in execution.outputs:
        if raw.get("kind") == "error":
            return CellError(
                ename=str(raw.get("ename") or "?"),
                evalue=str(raw.get("evalue") or "?"),
                traceback=list(raw.get("traceback") or []),
            )
    return None


def _stem(notebook_rel: str) -> str:
    """Extract a notebook's stem (drop path + extension) for cell ids."""
    return Path(notebook_rel).stem


def _env_hash_from_notebook(notebook: Notebook) -> str:
    """Derive an env-hash from the notebook's PEP-723 ``dependencies`` list."""
    if notebook.pep723_block is None:
        return hashing.env_hash_from_deps([])
    try:
        content = pep723_parse(notebook.pep723_block)
    except Exception:
        return hashing.env_hash_from_deps([])
    deps = content.get("dependencies", [])
    if not isinstance(deps, list):
        return hashing.env_hash_from_deps([])
    return hashing.env_hash_from_deps([str(d) for d in deps])


def _snapshot_artifacts(artifacts_dir: Path) -> dict[str, tuple[float, int]]:
    """Return ``{relative_path: (mtime, size)}`` for every file under ``artifacts_dir``."""
    result: dict[str, tuple[float, int]] = {}
    if not artifacts_dir.exists():
        return result
    for p in artifacts_dir.rglob("*"):
        if p.is_file():
            stat = p.stat()
            result[str(p)] = (stat.st_mtime, stat.st_size)
    return result


def _artifacts_diff(
    project_root: Path,
    before: dict[str, tuple[float, int]],
    after: dict[str, tuple[float, int]],
) -> list[ArtifactRecord]:
    """Return new or modified files (compared by mtime + size)."""
    records: list[ArtifactRecord] = []
    for full_path_str, (mtime, size) in sorted(after.items()):
        if before.get(full_path_str) == (mtime, size):
            continue
        full_path = Path(full_path_str)
        try:
            data = full_path.read_bytes()
        except OSError:
            continue
        digest = hashlib.sha256(data).hexdigest()
        rel = str(full_path.relative_to(project_root))
        records.append(ArtifactRecord(path=rel, sha256=digest, size=size, mime=None))
    return records


def _pending_meta_dir(cache_dir: Path) -> Path:
    return cache_dir / "pending-meta"


def _clear_pending_meta(cache_dir: Path) -> None:
    """Wipe the pending-meta directory before a cell runs.

    Defensive: if a previous run died mid-cell and left orphan entries, they
    must not leak into the next cell's manifest. Called at the start of each
    ``_run_one_cell`` invocation.
    """
    import contextlib

    d = _pending_meta_dir(cache_dir)
    if not d.exists():
        return
    for f in d.iterdir():
        if f.is_file():
            with contextlib.suppress(OSError):
                f.unlink()


def _apply_pending_meta(cache_dir: Path, artifacts: list[ArtifactRecord]) -> None:
    """Enrich ``artifacts`` with caption/notes/tags from pending-meta files.

    Each pending-meta JSON carries a path + metadata written by
    :func:`jellycell.api._record_artifact_metadata` during cell execution. We
    match by relative path and mutate the corresponding :class:`ArtifactRecord`
    in place. Files are deleted after processing so they don't leak between
    cells. Unmatched metadata (artifact not produced, or diff missed it) is
    silently discarded — the next run regenerates.
    """
    d = _pending_meta_dir(cache_dir)
    if not d.exists():
        return
    by_path = {art.path: art for art in artifacts}
    for f in sorted(d.iterdir()):
        if not f.is_file() or f.suffix != ".json":
            continue
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            f.unlink(missing_ok=True)
            continue
        path = payload.get("path")
        target = by_path.get(path) if isinstance(path, str) else None
        if target is not None:
            caption = payload.get("caption")
            notes = payload.get("notes")
            tags = payload.get("tags") or []
            if isinstance(caption, str):
                target.caption = caption
            if isinstance(notes, str):
                target.notes = notes
            if isinstance(tags, list):
                target.tags = [str(t) for t in tags]
        f.unlink(missing_ok=True)


def _translate_outputs(store: CacheStore, execution: CellExecution) -> list[OutputRecord]:
    """Convert kernel iopub dicts into :class:`OutputRecord`, storing blobs."""
    out: list[OutputRecord] = []
    for raw in execution.outputs:
        kind = raw.get("kind")
        if kind == "stream":
            text = raw.get("text", "")
            blob = store.put_blob(text.encode("utf-8"))
            out.append(StreamOutput(name=raw.get("name", "stdout"), blob=blob))
        elif kind == "display_data":
            for mime, data in (raw.get("data") or {}).items():
                blob = store.put_blob(_data_to_bytes(data, mime))
                out.append(DisplayDataOutput(mime=mime, blob=blob))
        elif kind == "execute_result":
            for mime, data in (raw.get("data") or {}).items():
                blob = store.put_blob(_data_to_bytes(data, mime))
                out.append(
                    ExecuteResultOutput(
                        mime=mime,
                        blob=blob,
                        execution_count=raw.get("execution_count"),
                    )
                )
        elif kind == "error":
            out.append(
                ErrorOutput(
                    ename=raw.get("ename", "?"),
                    evalue=raw.get("evalue", "?"),
                    traceback=list(raw.get("traceback") or []),
                )
            )
    return out


def _data_to_bytes(data: Any, mime: str | None = None) -> bytes:
    """Normalize display-data values to the raw bytes we'll store.

    The Jupyter message protocol delivers binary mime types (e.g., ``image/png``)
    as base64-encoded strings. We decode them back to raw bytes here so the
    cache stores canonical blobs; callers that want base64 (e.g., ``<img src="data:…">``)
    re-encode at render time.
    """
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        if _is_binary_mime(mime):
            try:
                return base64.b64decode(data, validate=True)
            except (binascii.Error, ValueError):
                return data.encode("utf-8")
        return data.encode("utf-8")
    import json as _json

    return _json.dumps(data).encode("utf-8")


def _is_binary_mime(mime: str | None) -> bool:
    """Jupyter's protocol base64-encodes most image types except SVG."""
    if not mime:
        return False
    if mime == "image/svg+xml":
        return False
    return mime.startswith("image/") or mime == "application/pdf"


def _setup_prelude(
    project: Project,
    notebook_rel: str,
    cell_id: str,
    cell_name: str | None,
) -> str:
    """Python snippet run in the kernel before each cell to install RunContext.

    Also ``os.chdir(project.root)`` so that relative paths inside a cell
    resolve against the project root — matches the developer's mental model
    when they run the notebook outside jellycell.
    """
    name_lit = repr(cell_name) if cell_name is not None else "None"
    return (
        "import os as _JC_os\n"
        "from pathlib import Path as _JC_Path\n"
        "from jellycell.paths import Project as _JC_Project\n"
        "from jellycell.run.context import (\n"
        "    RunContext as _JC_RunContext,\n"
        "    set_context as _jc_set_context,\n"
        ")\n"
        f"_JC_os.chdir({str(project.root)!r})\n"
        f"_jc_project = _JC_Project.from_path(_JC_Path({str(project.root)!r}))\n"
        "_jc_set_context(_JC_RunContext(\n"
        f"    notebook={notebook_rel!r},\n"
        f"    cell_id={cell_id!r},\n"
        f"    cell_name={name_lit},\n"
        "    project=_jc_project,\n"
        "))\n"
        "import jellycell.api as jc\n"
    )
