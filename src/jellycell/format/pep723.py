"""PEP-723 script block extraction and re-insertion.

Jupytext treats the ``# /// script`` block as a regular code cell and mutates
it on first round-trip (prepending a ``# %%`` marker). We strip the block
pre-parse and reinsert it verbatim post-write (spec §1 "piggyback map",
§2.2 "Format").

The block must be at the top of the file per spec §7; :func:`position_ok` is
used by the ``pep723-position`` lint rule.

See Also:
    PEP 723 — https://peps.python.org/pep-0723/
"""

from __future__ import annotations

import re
import tomllib
from typing import Any

#: Canonical PEP-723 regex (from PEP 723 specification).
PEP723_PATTERN = re.compile(
    r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$"
)


def extract(text: str) -> tuple[str | None, str]:
    """Extract the PEP-723 ``script`` block from ``text``.

    Returns:
        ``(block, body)``. ``block`` is the verbatim matched substring or
        ``None`` if no block is present. ``body`` is ``text`` with the block
        removed. Round-trip byte-exact via :func:`insert`.
    """
    match = PEP723_PATTERN.search(text)
    if match is None:
        return None, text
    if match.group("type") != "script":
        # Only `script` blocks are PEP-723 sanctioned. Leave other types alone.
        return None, text
    block = match.group(0)
    body = text[: match.start()] + text[match.end() :]
    return block, body


def insert(block: str | None, body: str) -> str:
    """Insert a PEP-723 block ahead of ``body``.

    Inverse of :func:`extract` for block-at-top inputs:
    ``insert(*extract(text)) == text``.
    """
    if block is None:
        return body
    return block + body


def parse_content(block: str) -> dict[str, Any]:
    """Parse the TOML content of a PEP-723 block (strips the ``# `` prefixes)."""
    lines = block.splitlines()
    if not lines or not lines[0].startswith("# /// "):
        raise ValueError(f"Not a PEP-723 block: {lines[0] if lines else ''!r}")
    if lines[-1] != "# ///":
        raise ValueError(f"Expected closing '# ///', got {lines[-1]!r}")
    content_lines: list[str] = []
    for line in lines[1:-1]:
        if line == "#":
            content_lines.append("")
        elif line.startswith("# "):
            content_lines.append(line[2:])
        else:
            raise ValueError(f"Invalid PEP-723 content line: {line!r}")
    return tomllib.loads("\n".join(content_lines))


def jellycell_overrides(block: str | None) -> dict[str, Any]:
    """Extract ``[tool.jellycell]`` overrides from a PEP-723 block, if any.

    Returns an empty dict if no block, no ``[tool]``, or no ``[tool.jellycell]``.
    """
    if block is None:
        return {}
    parsed = parse_content(block)
    tool = parsed.get("tool", {})
    if not isinstance(tool, dict):
        return {}
    overrides = tool.get("jellycell", {})
    if not isinstance(overrides, dict):
        return {}
    return overrides


def position_ok(text: str) -> bool:
    """Return ``True`` iff any PEP-723 block is at the top of the file.

    Implements the ``pep723-position`` lint rule (spec §7): a block is
    well-positioned iff only whitespace precedes its opening ``# /// script``.
    """
    match = PEP723_PATTERN.search(text)
    if match is None:
        return True
    return text[: match.start()].strip() == ""


def move_to_top(text: str) -> str:
    """Move a mid-file PEP-723 block to the top of ``text``.

    No-op if there's no block or the block is already at the top.
    Auto-fix for the ``pep723-position`` lint violation.
    """
    match = PEP723_PATTERN.search(text)
    if match is None:
        return text
    if position_ok(text):
        return text
    block = match.group(0)
    before = text[: match.start()]
    after = text[match.end() :]
    body = (before + after).strip("\n")
    if not body:
        return f"{block}\n"
    return f"{block}\n\n{body}\n"
