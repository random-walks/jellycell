"""Entry point for ``python -m jellycell`` — delegates to :mod:`jellycell.cli.app`."""

from __future__ import annotations

from jellycell.cli.app import app


def main() -> None:
    """Entry for ``python -m jellycell``."""
    app()


if __name__ == "__main__":
    main()
