"""Cache key derivation — the spec §10.2 contract.

The public surface here is tiny and frozen. **Any change to normalization,
input set, or composition requires the §10.2 ceremony**:

1. Bump :data:`jellycell._version.MINOR_VERSION`.
2. Regenerate the regression snapshot in ``tests/unit/test_hashing.py``.
3. Add a ``CHANGELOG.md`` entry under ``[Unreleased] ### Changed``.

See CLAUDE.md for the full rationale.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from jellycell._version import MINOR_VERSION

#: Separator between components. Using ASCII Unit Separator (U+001F) which
#: never appears in normalized source or sha256 hex digests.
_SEP = b"\x1f"


def normalize_source(source: str) -> str:
    """Normalize cell source text for stable hashing (spec §2.3).

    - Line endings → ``\\n``.
    - Per-line trailing whitespace stripped.
    - Leading/trailing blank lines removed.
    - Empty result returns empty string (no trailing newline).
    """
    text = source.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def source_hash(source: str) -> str:
    """Hex sha256 of normalized source. Equivalent to the source component of the key."""
    return hashlib.sha256(normalize_source(source).encode("utf-8")).hexdigest()


def env_hash_from_deps(deps: Sequence[str]) -> str:
    """Fallback env-hash: sha256 of sorted unique dep specifiers.

    Used when no lockfile hash is available. Callers that have a lockfile
    should hash the lockfile bytes directly.
    """
    h = hashlib.sha256()
    for dep in sorted(set(deps)):
        h.update(dep.encode("utf-8"))
        h.update(_SEP)
    return h.hexdigest()


def key(
    *,
    source: str,
    dep_keys: Sequence[str],
    env_hash: str,
) -> str:
    """Derive the content-addressed cache key for a cell execution (spec §2.3).

    Args:
        source: Raw cell source text; normalized internally.
        dep_keys: Cache keys of every cell this one depends on. Sorted
            internally so dep declaration order doesn't affect the key.
        env_hash: Hash of the resolved environment (lockfile bytes, or
            :func:`env_hash_from_deps` fallback).

    Returns:
        Lowercase hex sha256 digest.

    **Changing this function breaks spec §10.2.** Follow the ceremony before
    editing.
    """
    h = hashlib.sha256()
    h.update(normalize_source(source).encode("utf-8"))
    h.update(_SEP)
    for dep_key in sorted(dep_keys):
        h.update(dep_key.encode("ascii"))
        h.update(_SEP)
    h.update(_SEP)  # end-of-deps sentinel
    h.update(env_hash.encode("ascii"))
    h.update(_SEP)
    h.update(str(MINOR_VERSION).encode("ascii"))
    return h.hexdigest()
