"""Entry point shim for `python lab_cli.py ...`."""

from cli.lab_cli import main


if __name__ == "__main__":
    raise SystemExit(main())
