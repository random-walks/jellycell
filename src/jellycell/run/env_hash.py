"""Environment hashing with lockfile detection.

Spec §2.3 says the cache key incorporates an ``env_hash``. v0.1 hashed only
the PEP-723 ``dependencies`` list, which silently shared caches between
environments that resolved to different concrete versions.

This module picks the best available signal:

1. If ``uv.lock`` exists at the project root: hash its bytes. Users who care
   about reproducibility commit a lockfile and get version-level invalidation.
2. Else if ``poetry.lock`` exists: hash its bytes.
3. Else fall back to hashing sorted PEP-723 dependency specifiers — best
   effort, matches v0.1 behavior for projects without lockfiles.

The precedence is deliberate: a lockfile is a stronger signal than the
dependency list, and the first wins.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from jellycell.cache.hashing import env_hash_from_deps as _env_hash_from_deps
from jellycell.format.cells import Notebook
from jellycell.format.pep723 import parse_content
from jellycell.paths import Project


def compute_env_hash(project: Project, notebook: Notebook) -> str:
    """Compute an environment hash for this notebook under ``project``.

    Checks lockfiles first; falls back to the PEP-723 dependencies list.
    """
    for lockfile_name in ("uv.lock", "poetry.lock"):
        lockfile = project.root / lockfile_name
        if lockfile.exists():
            return _hash_lockfile(lockfile, lockfile_name)

    return _env_hash_from_pep723(notebook)


def _hash_lockfile(path: Path, kind: str) -> str:
    """SHA256 of the lockfile bytes, prefixed with the lockfile kind.

    Prefixing prevents cross-hash collisions if the same byte-sequence happens
    to appear in two different lockfile formats (astronomically unlikely but
    cheap insurance).
    """
    h = hashlib.sha256()
    h.update(kind.encode("ascii"))
    h.update(b"\x1f")
    h.update(path.read_bytes())
    return h.hexdigest()


def _env_hash_from_pep723(notebook: Notebook) -> str:
    """Fallback: hash the PEP-723 ``dependencies`` list."""
    if notebook.pep723_block is None:
        return _env_hash_from_deps([])
    try:
        content = parse_content(notebook.pep723_block)
    except Exception:
        return _env_hash_from_deps([])
    deps = content.get("dependencies", [])
    if not isinstance(deps, list):
        return _env_hash_from_deps([])
    return _env_hash_from_deps([str(d) for d in deps])
