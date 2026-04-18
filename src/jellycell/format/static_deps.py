"""Static AST extraction of implicit cell dependencies.

Spec §2.5 says to AST-walk ``jc.deps("a", "b")`` calls statically so the
arguments enter the cache key before the cell runs. This module does that,
plus two additional signals:

- ``jc.load("artifacts/foo.json")`` with a literal path: the artifact's
  producer cell becomes an implicit dep (when the cache index knows about it).
- ``jc.deps(...)`` with non-string or non-constant arguments: silently
  skipped — we only resolve call-site constants.

Runtime dep registration (``ctx.declared_deps``) complements this for
dynamic cases but can't affect the current cell's cache key.
"""

from __future__ import annotations

import ast

#: Function names we care about on the ``jc`` namespace.
_DEPS_CALLS = {"deps"}
_LOAD_CALLS = {"load"}


def extract_static_deps(source: str) -> list[str]:
    """Extract named deps declared via ``jc.deps(...)`` in cell source.

    Returns an ordered, deduplicated list of dep names. Non-constant args
    (e.g., ``jc.deps(some_var)``) are skipped.
    """
    tree = _safe_parse(source)
    if tree is None:
        return []
    names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_jc_call(node.func, _DEPS_CALLS):
            continue
        for arg in node.args:
            if (
                isinstance(arg, ast.Constant)
                and isinstance(arg.value, str)
                and arg.value not in names
            ):
                names.append(arg.value)
    return names


def extract_loaded_paths(source: str) -> list[str]:
    """Extract literal paths from ``jc.load("...")`` calls.

    Callers should resolve each path to a producer cell via the cache index.
    """
    tree = _safe_parse(source)
    if tree is None:
        return []
    paths: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_jc_call(node.func, _LOAD_CALLS):
            continue
        if not node.args:
            continue
        first = node.args[0]
        if (
            isinstance(first, ast.Constant)
            and isinstance(first.value, str)
            and first.value not in paths
        ):
            paths.append(first.value)
    return paths


def _safe_parse(source: str) -> ast.AST | None:
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _is_jc_call(func: ast.expr, names: set[str]) -> bool:
    """True if ``func`` is ``jc.<name>`` or ``jellycell.api.<name>`` for a name in ``names``."""
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr not in names:
        return False
    # jc.<name>(...) — simple form
    if isinstance(func.value, ast.Name) and func.value.id in {"jc", "jellycell"}:
        return True
    # jellycell.api.<name>(...) — fully qualified
    if isinstance(func.value, ast.Attribute) and func.value.attr == "api":
        inner = func.value.value
        if isinstance(inner, ast.Name) and inner.id == "jellycell":
            return True
    return False
