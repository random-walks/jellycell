"""Parse jupytext cell-tag lists into :class:`CellSpec` instances.

Tags in jupytext percent format live in ``cell.metadata.tags`` as a list of
strings (spec §7). Examples::

    ["jc.load", "name=raw"]
    ["jc.step", "name=summary", "deps=raw"]
    ["jc.step", "name=summary", "deps=raw", "deps=env"]    # multi-dep
    ["jc.step", "deps=raw;env"]                            # semicolon syntax
    ["jc.figure", "deps=summary", "timeout=60"]

nbformat's JSON schema forbids commas in tag strings (``^[^,]+$``). Multi-dep
cells must use either multiple ``deps=`` tags or ``;`` as the separator.
``render_tags`` always emits multiple ``deps=`` tags so the output is
nbformat-safe.
"""

from __future__ import annotations

import re
from typing import get_args

from jellycell.format.cells import CellKind, CellSpec

#: Tag prefix mapping to ``CellKind`` values.
KIND_TAGS: dict[str, CellKind] = {f"jc.{k}": k for k in get_args(CellKind)}

#: Split deps on either ``,`` or ``;``. Commas work when tags are set
#: programmatically (they won't round-trip through jupytext, but are handy
#: in tests); semicolons are the nbformat-safe form.
_DEP_SPLIT = re.compile(r"[,;]")


class TagParseError(ValueError):
    """Raised for malformed cell tags."""


def parse_tags(tags: list[str]) -> CellSpec:
    """Parse a tag list into a :class:`CellSpec`.

    Unknown ``jc.*`` tags raise :class:`TagParseError`; unknown non-``jc.*``
    tags are ignored (jupytext/papermill/etc. may set their own). Multiple
    ``deps=`` tags accumulate.
    """
    kind: CellKind = "step"
    name: str | None = None
    deps: list[str] = []
    timeout_s: int | None = None

    seen_kind = False
    for tag in tags:
        if tag in KIND_TAGS:
            if seen_kind:
                raise TagParseError(f"Multiple kind tags on one cell: {tags!r}")
            kind = KIND_TAGS[tag]
            seen_kind = True
            continue
        if tag.startswith("jc."):
            raise TagParseError(f"Unknown jc.* kind tag: {tag!r}")
        if "=" not in tag:
            continue  # opaque foreign tag — ignore
        key, _, value = tag.partition("=")
        key = key.strip()
        value = value.strip()
        if key == "name":
            name = value or None
        elif key == "deps":
            for dep in _DEP_SPLIT.split(value):
                dep = dep.strip()
                if dep and dep not in deps:
                    deps.append(dep)
        elif key == "timeout":
            try:
                timeout_s = int(value)
            except ValueError as exc:
                raise TagParseError(f"timeout= expects integer seconds, got {value!r}") from exc
        # Other attrs are ignored for forward-compat.

    return CellSpec(kind=kind, name=name, deps=deps, timeout_s=timeout_s)


def render_tags(spec: CellSpec) -> list[str]:
    """Inverse of :func:`parse_tags` — produce a canonical tag list for a spec.

    Emits one ``deps=<name>`` tag per dep so the output round-trips through
    nbformat's ``^[^,]+$`` constraint on tag strings.
    """
    out: list[str] = [f"jc.{spec.kind}"]
    if spec.name is not None:
        out.append(f"name={spec.name}")
    for dep in spec.deps:
        out.append(f"deps={dep}")
    if spec.timeout_s is not None:
        out.append(f"timeout={spec.timeout_s}")
    return out
