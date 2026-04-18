"""Lint rule registry and rule implementations.

Each rule is a function ``(Project) -> list[Violation]``. Fixers apply
auto-fixes for violations marked ``fixable=True``.

Rules in this file:

- ``layout`` — all declared path roots exist (always on).
- ``pep723-position`` — the PEP-723 block (if any) is at the top (always on).
- ``enforce-artifact-paths`` — ``jc.save`` / ``jc.figure`` / ``jc.table``
  calls write into ``paths.artifacts``. Gated by ``lint.enforce_artifact_paths``.
- ``enforce-declared-deps`` — named cells that reference another cell's name
  via ``jc.load`` must declare it in ``deps=`` (or have it picked up by the
  AST walker). Gated by ``lint.enforce_declared_deps``.
- ``warn-on-large-cell-output`` — cached outputs exceeding the size threshold
  get a (non-fixable) warning. Gated by ``lint.warn_on_large_cell_output``.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from jellycell.format import pep723, static_deps
from jellycell.format.parse import parse_text
from jellycell.paths import Project


@dataclass(frozen=True)
class Violation:
    """A single lint finding.

    ``fixable=True`` indicates a registered fixer exists and can attempt to
    resolve this violation automatically.
    """

    rule: str
    path: Path | None
    line: int | None
    message: str
    fixable: bool


RuleFn = Callable[[Project], list[Violation]]
FixerFn = Callable[[Project, Violation], bool]


def rule_layout(project: Project) -> list[Violation]:
    """Check that declared path roots exist (spec §2.1)."""
    violations: list[Violation] = []
    for root in project.declared_roots:
        # cache_dir is implicitly created by the cache layer on first run.
        if root == project.cache_dir:
            continue
        if not root.exists():
            relative = root.relative_to(project.root) if root.is_absolute() else root
            violations.append(
                Violation(
                    rule="layout",
                    path=root,
                    line=None,
                    message=f"Declared path {relative}/ does not exist",
                    fixable=True,
                )
            )
    return violations


def fix_layout(project: Project, violation: Violation) -> bool:
    """Create the missing directory."""
    if violation.path is None:
        return False
    violation.path.mkdir(parents=True, exist_ok=True)
    return True


def rule_pep723_position(project: Project) -> list[Violation]:
    """Check every notebook's PEP-723 block is at the top of the file (spec §7)."""
    violations: list[Violation] = []
    nb_dir = project.notebooks_dir
    if not nb_dir.exists():
        return []
    for path in sorted(nb_dir.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not pep723.position_ok(text):
            relative = path.relative_to(project.root)
            violations.append(
                Violation(
                    rule="pep723-position",
                    path=path,
                    line=None,
                    message=f"PEP-723 block is not at the top of {relative}",
                    fixable=True,
                )
            )
    return violations


def fix_pep723_position(project: Project, violation: Violation) -> bool:
    """Auto-fix by moving the block to the top of the file."""
    if violation.path is None:
        return False
    text = violation.path.read_text(encoding="utf-8")
    fixed = pep723.move_to_top(text)
    if fixed == text:
        return False
    violation.path.write_text(fixed, encoding="utf-8")
    return True


def rule_enforce_artifact_paths(project: Project) -> list[Violation]:
    """AST-scan notebooks for ``jc.save/figure/table`` calls with paths outside ``artifacts/``."""
    if not project.config.lint.enforce_artifact_paths:
        return []
    artifacts_prefix = project.config.paths.artifacts.rstrip("/") + "/"
    violations: list[Violation] = []
    nb_dir = project.notebooks_dir
    if not nb_dir.exists():
        return []
    for path in sorted(nb_dir.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            target = _jc_write_call_target(node)
            if target is None:
                continue
            if not target.startswith(artifacts_prefix):
                relative = path.relative_to(project.root)
                violations.append(
                    Violation(
                        rule="enforce-artifact-paths",
                        path=path,
                        line=node.lineno,
                        message=(
                            f"{relative}:{node.lineno}: jc.save/figure/table target "
                            f"{target!r} must live under {artifacts_prefix}"
                        ),
                        fixable=False,
                    )
                )
    return violations


def rule_enforce_declared_deps(project: Project) -> list[Violation]:
    """Cells that ``jc.load(...)`` from another cell's artifact must declare the dep."""
    if not project.config.lint.enforce_declared_deps:
        return []
    violations: list[Violation] = []
    nb_dir = project.notebooks_dir
    if not nb_dir.exists():
        return []

    from jellycell.cache.index import CacheIndex

    index_path = project.cache_dir / "state.db"
    if not index_path.exists():
        return []
    idx = CacheIndex(index_path)
    try:
        for path in sorted(nb_dir.rglob("*.py")):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            try:
                nb = parse_text(text)
            except Exception:
                continue
            for cell in nb.cells:
                if cell.cell_type != "code":
                    continue
                declared = set(cell.spec.deps)
                declared.update(static_deps.extract_static_deps(cell.source))
                loaded = static_deps.extract_loaded_paths(cell.source)
                for artifact_path in loaded:
                    producer = idx.find_producer(artifact_path)
                    if not producer:
                        continue
                    producer_name = producer.get("cell_name")
                    if producer_name and producer_name not in declared:
                        relative = path.relative_to(project.root)
                        violations.append(
                            Violation(
                                rule="enforce-declared-deps",
                                path=path,
                                line=None,
                                message=(
                                    f"{relative}: cell {cell.spec.name or 'anon'!r} "
                                    f"jc.load's artifacts from {producer_name!r} but "
                                    f"doesn't declare deps={producer_name} — add it to the tag"
                                ),
                                fixable=False,
                            )
                        )
    finally:
        idx.close()
    return violations


def rule_warn_on_large_cell_output(project: Project) -> list[Violation]:
    """Cached cells whose total output size exceeds ``warn_on_large_cell_output``."""
    limit_spec = project.config.lint.warn_on_large_cell_output
    try:
        limit_bytes = _parse_size(limit_spec)
    except ValueError:
        return []

    from jellycell.cache.index import CacheIndex
    from jellycell.cache.store import CacheStore

    index_path = project.cache_dir / "state.db"
    if not index_path.exists():
        return []

    violations: list[Violation] = []
    store = CacheStore(project.cache_dir)
    idx = CacheIndex(index_path)
    try:
        for row in idx.list_all():
            try:
                manifest = store.get_manifest(str(row["cache_key"]))
            except KeyError:
                continue
            total = 0
            for output in manifest.outputs:
                blob = getattr(output, "blob", None)
                if blob is None:
                    continue
                try:
                    total += len(store.get_blob(blob))
                except KeyError:
                    continue
            if total > limit_bytes:
                violations.append(
                    Violation(
                        rule="warn-on-large-cell-output",
                        path=None,
                        line=None,
                        message=(
                            f"{manifest.notebook}:{manifest.cell_id} "
                            f"cached outputs total {total:,}B > {limit_bytes:,}B limit"
                        ),
                        fixable=False,
                    )
                )
    finally:
        idx.close()
        store.close()
    return violations


_SIZE_RE = re.compile(r"^\s*(?P<n>\d+)\s*(?P<u>[KMG]?B?)?\s*$", re.IGNORECASE)
_SIZE_MULT = {"": 1, "B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}


def _parse_size(spec: str) -> int:
    m = _SIZE_RE.match(spec)
    if not m:
        raise ValueError(f"invalid size {spec!r}")
    unit = m.group("u").upper() if m.group("u") else ""
    if unit not in _SIZE_MULT:
        raise ValueError(f"invalid unit in {spec!r}")
    return int(m.group("n")) * _SIZE_MULT[unit]


def _jc_write_call_target(node: ast.Call) -> str | None:
    """Return the path-arg of a ``jc.save(x, "path")`` / ``jc.figure(path=...)`` call."""
    func = node.func
    if not isinstance(func, ast.Attribute):
        return None
    if func.attr not in {"save", "figure", "table"}:
        return None
    # Accept jc.X(...) or jellycell.api.X(...)
    owner = func.value
    if (isinstance(owner, ast.Name) and owner.id in {"jc", "jellycell"}) or (
        isinstance(owner, ast.Attribute)
        and owner.attr == "api"
        and isinstance(owner.value, ast.Name)
        and owner.value.id == "jellycell"
    ):
        pass
    else:
        return None

    # jc.save(obj, "path")  → positional[1]
    # jc.figure(path="x")   → keyword path=
    # jc.table(df, name=…)  → name-kwarg, no path — skip
    if func.attr == "save":
        if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
            value = node.args[1].value
            if isinstance(value, str):
                return value
        for kw in node.keywords:
            if (
                kw.arg == "path"
                and isinstance(kw.value, ast.Constant)
                and isinstance(kw.value.value, str)
            ):
                return kw.value.value
    if func.attr == "figure":
        if (
            node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            return node.args[0].value
        for kw in node.keywords:
            if (
                kw.arg == "path"
                and isinstance(kw.value, ast.Constant)
                and isinstance(kw.value.value, str)
            ):
                return kw.value.value
    # jc.table doesn't take an explicit path in our API; fall through.
    return None


RULES: dict[str, RuleFn] = {
    "layout": rule_layout,
    "pep723-position": rule_pep723_position,
    "enforce-artifact-paths": rule_enforce_artifact_paths,
    "enforce-declared-deps": rule_enforce_declared_deps,
    "warn-on-large-cell-output": rule_warn_on_large_cell_output,
}

FIXERS: dict[str, FixerFn] = {
    "layout": fix_layout,
    "pep723-position": fix_pep723_position,
}


def run_all(project: Project) -> list[Violation]:
    """Run every registered rule. Returns violations in a stable order."""
    violations: list[Violation] = []
    for name in sorted(RULES):
        violations.extend(RULES[name](project))
    return violations


def auto_fix(project: Project, violations: list[Violation]) -> list[Violation]:
    """Apply registered fixers. Returns the list of remaining violations.

    Violations are considered "remaining" if:

    - ``fixable`` is False, or
    - No fixer is registered for the rule, or
    - The fixer returned ``False`` (couldn't fix).
    """
    remaining: list[Violation] = []
    for v in violations:
        if not v.fixable:
            remaining.append(v)
            continue
        fixer = FIXERS.get(v.rule)
        if fixer is None:
            remaining.append(v)
            continue
        if not fixer(project, v):
            remaining.append(v)
    return remaining
