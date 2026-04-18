"""Append-only analysis journal for ``jellycell run``.

Writes one markdown section per invocation to ``manuscripts/journal.md``
(or the path configured in ``[journal] path``). Enabled by default — the
audit trail is usually more valuable than an empty file, and the entry
is small + human-readable so it stays useful even in clean projects.

The journal is **append-only** from jellycell's side. Users are free to
hand-edit existing entries (commentary, corrections, retrospective
notes); the next ``jellycell run`` only adds new entries at the bottom
without touching prior text.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from jellycell.cache.index import CacheIndex
from jellycell.cache.manifest import ArtifactRecord
from jellycell.cache.store import CacheStore
from jellycell.paths import Project
from jellycell.run import RunReport


def append_entry(
    project: Project,
    report: RunReport,
    *,
    message: str | None = None,
    now: datetime | None = None,
) -> Path | None:
    """Append a journal entry for ``report``. Returns the journal path, or None if disabled."""
    cfg = project.config.journal
    if not cfg.enabled:
        return None

    target = project.manuscripts_dir / cfg.path
    target.parent.mkdir(parents=True, exist_ok=True)

    artifacts = _collect_artifacts(project, report)
    entry = _format_entry(
        report=report,
        artifacts=artifacts,
        message=message,
        now=now or datetime.now(UTC),
    )

    if target.exists():
        prior = target.read_text(encoding="utf-8").rstrip("\n")
        new = f"{prior}\n\n{entry}\n"
    else:
        new = f"{_header(project)}\n\n{entry}\n"
    target.write_text(new, encoding="utf-8")
    return target


def _header(project: Project) -> str:
    """Top-of-file blurb written once when the journal is first created."""
    return (
        f"# {project.config.project.name} — analysis journal\n\n"
        "Append-only run log written by `jellycell run`. Each section below is\n"
        "one invocation: timestamp, notebook, cell-change summary, and any new\n"
        "or updated artifacts. Safe to hand-edit for commentary — the next\n"
        "`jellycell run` only appends at the bottom.\n\n"
        "Disable via `[journal] enabled = false` in `jellycell.toml`."
    )


def _collect_artifacts(project: Project, report: RunReport) -> list[ArtifactRecord]:
    """Pull artifact records for every non-cached cell this run produced."""
    fresh_keys = [c.cache_key for c in report.cell_results if c.status == "ok" and c.cache_key]
    if not fresh_keys:
        return []
    store = CacheStore(project.cache_dir)
    idx = CacheIndex(project.cache_dir / "state.db")
    records: list[ArtifactRecord] = []
    try:
        for key in fresh_keys:
            try:
                manifest = store.get_manifest(key)
            except KeyError:
                continue
            records.extend(manifest.artifacts)
    finally:
        idx.close()
        store.close()
    return records


def _format_entry(
    *,
    report: RunReport,
    artifacts: list[ArtifactRecord],
    message: str | None,
    now: datetime,
) -> str:
    stamp = now.isoformat(timespec="seconds")
    # Header line carries the searchable metadata so grep-by-date works.
    lines: list[str] = [f"## {stamp} — `{report.notebook}`", ""]

    counts = _counts(report)
    summary = (
        f"**Status:** {report.status} · "
        f"{counts['ok']} ran · {counts['cached']} cached · "
        f"{counts['error']} errored · {report.total_duration_ms}ms"
    )
    if message:
        # Emphasise so reviewers skimming the journal see intent first.
        summary += f" · _{message}_"
    lines.append(f"> {summary}")

    if artifacts:
        lines.append("")
        lines.append("**Artifacts:**")
        for art in artifacts:
            note = f" — {art.caption}" if art.caption else ""
            lines.append(f"- `{art.path}` ({_humanize_bytes(art.size)}){note}")

    if report.large_artifacts:
        lines.append("")
        lines.append(f"**Large-file warnings** (> {report.large_artifacts[0].limit_mb} MB):")
        for w in report.large_artifacts:
            lines.append(f"- `{w.path}` — {w.size_mb:.1f} MB")

    errors = [c for c in report.cell_results if c.status == "error"]
    if errors:
        lines.append("")
        lines.append("**Errors:**")
        for err in errors:
            info = err.error
            name = f" ({err.cell_name})" if err.cell_name else ""
            if info is not None:
                lines.append(f"- `{err.cell_id}{name}` — {info.ename}: {info.evalue}")
            else:
                lines.append(f"- `{err.cell_id}{name}`")

    return "\n".join(lines)


def _counts(report: RunReport) -> dict[str, int]:
    counts = {"ok": 0, "cached": 0, "error": 0, "skipped": 0}
    for c in report.cell_results:
        counts[c.status] = counts.get(c.status, 0) + 1
    return counts


def _humanize_bytes(n: int) -> str:
    """Short, human-friendly size (e.g. ``3.2 KB``, ``14 MB``)."""
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    if n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    return f"{n / (1024 * 1024 * 1024):.2f} GB"


__all__ = ["append_entry"]
