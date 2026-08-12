"""Installed console-script adapter for the existing JSON CLI."""

from __future__ import annotations

import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Run the established CLI while preserving conventional help behavior."""

    args = list(sys.argv[1:] if argv is None else argv)
    if "-h" in args or "--help" in args:
        from .lab_cli import build_parser

        parser = build_parser()
        parser.prog = "ai-teaching-agent"
        try:
            parser.parse_args(args)
        except SystemExit as exc:
            return int(exc.code or 0)
        return 0

    from .lab_cli import main as json_cli_main

    return json_cli_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
