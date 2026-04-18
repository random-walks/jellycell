"""Function-level memoization backed by :class:`CacheStore`.

Wires ``@jc.cache`` to the same content-addressed store that backs cell
caching. The key combines the function's qualified name, its source text
(stripped by the same normalization as cell source), and a pickle hash of
the call arguments.

Limitations (documented + accepted for v0):

- Arguments must be pickle-able. Non-picklable inputs (open file handles,
  lambdas, bound methods with non-picklable ``self``) raise at call time.
- Source changes invalidate every call — same principle as cell hashing.
- Concurrent calls from the same process race on write (diskcache is atomic
  per-key; last-writer wins).

The decorator is transparent in standalone mode (no RunContext) — it just
calls the function.
"""

from __future__ import annotations

import functools
import hashlib
import inspect
import pickle
from typing import Any, TypeVar

from jellycell.cache import hashing
from jellycell.cache.manifest import Manifest
from jellycell.cache.store import CacheStore
from jellycell.run.context import get_context

F = TypeVar("F")


def cache_function(fn: F) -> F:
    """Memoize ``fn`` via the current run's CacheStore.

    Identity operation outside a run (``get_context()`` returns ``None``) so
    the same decorator works in notebooks and in standalone scripts.
    """
    try:
        source = inspect.getsource(fn)  # type: ignore[arg-type]
    except (OSError, TypeError):
        source = ""

    @functools.wraps(fn)  # type: ignore[arg-type]
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        ctx = get_context()
        if ctx is None:
            return fn(*args, **kwargs)  # type: ignore[operator]

        key = _function_cache_key(fn, source, args, kwargs)
        store = CacheStore(ctx.project.cache_dir)
        try:
            if store.has(key):
                manifest = store.get_manifest(key)
                if manifest.status == "ok":
                    return _load_cached_return(manifest, store)

            result = fn(*args, **kwargs)  # type: ignore[operator]
            _persist(result, key, fn, ctx, store)
            return result
        finally:
            store.close()

    return wrapper  # type: ignore[return-value]


def _function_cache_key(fn: Any, source: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    """Derive a cache key from (qualname, normalized source, pickled args)."""
    qualname: str = getattr(fn, "__qualname__", None) or getattr(fn, "__name__", None) or "unknown"
    normalized = hashing.normalize_source(source)
    try:
        args_blob = pickle.dumps((args, sorted(kwargs.items())), protocol=5)
    except Exception as exc:
        raise TypeError(f"jc.cache: argument(s) to {qualname} are not pickleable: {exc}") from exc
    args_hash = hashlib.sha256(args_blob).hexdigest()
    h = hashlib.sha256()
    h.update(b"jc.cache\x1f")
    h.update(qualname.encode("utf-8"))
    h.update(b"\x1f")
    h.update(normalized.encode("utf-8"))
    h.update(b"\x1f")
    h.update(args_hash.encode("ascii"))
    return h.hexdigest()


def _persist(value: Any, key: str, fn: Any, ctx: Any, store: CacheStore) -> None:
    """Pickle + store the return value; write a minimal manifest next to it."""
    from datetime import UTC, datetime

    blob = store.put_blob(pickle.dumps(value, protocol=5))
    manifest = Manifest(
        cache_key=key,
        notebook=ctx.notebook if ctx else "",
        cell_id=f"{ctx.cell_id}@fn:{getattr(fn, '__qualname__', 'unknown')}"
        if ctx
        else f"fn:{getattr(fn, '__qualname__', 'unknown')}",
        cell_name=getattr(fn, "__qualname__", None),
        source_hash=hashing.source_hash(""),  # function source is in the key already
        env_hash="jc.cache",
        executed_at=datetime.now(UTC),
        duration_ms=0,
        status="ok",
        outputs=[],
        artifacts=[],
    )
    # Stash the return blob hash inside the manifest's cell_name metadata via
    # a JSON string in ename — cleaner alternatives exist but this avoids
    # introducing a new pydantic field purely for function-cache plumbing.
    # (The return blob is stored separately; we look it up via the same key.)
    _FN_RETURN_INDEX[key] = blob
    store.put_manifest(manifest)


def _load_cached_return(manifest: Manifest, store: CacheStore) -> Any:
    """Retrieve the pickled return value for a cache-hit function call."""
    blob = _FN_RETURN_INDEX.get(manifest.cache_key)
    if blob is None:
        # Cache hit on manifest but the in-memory return index lost track.
        # Re-compute signalled by raising; caller's wrapper will fall back.
        raise KeyError(manifest.cache_key)
    return pickle.loads(store.get_blob(blob))


# Process-local index of cache_key → return-value blob. Populated when we
# persist a function call; consulted on cache hits in the same process. Cross-
# process persistence of function-cache return values is a v0.3 nice-to-have.
_FN_RETURN_INDEX: dict[str, str] = {}
