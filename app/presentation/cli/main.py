from __future__ import annotations

import argparse
import sys
import os
import traceback

from app.bootstrap.runtime import init_environment
from app.presentation.cli.flow import run_cli


def main(argv: list[str] | None = None) -> int:
    if os.environ.get("OBD_CLI_TRACE") == "1":
        stack = "".join(traceback.format_stack(limit=6)).rstrip()
        print(
            f"[OBD_CLI_TRACE] pid={os.getpid()} argv={sys.argv} file={__file__}\n{stack}",
            file=sys.stderr,
        )

    parser = argparse.ArgumentParser(
        prog="app_cli",
        description="OBD-II diagnostics CLI",
        add_help=True,
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demo mode without hardware",
    )
    parsed_args, _unknown = parser.parse_known_args(argv or sys.argv[1:])

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        if parsed_args.demo:
            init_environment()
            run_cli(demo=True)
            return 0
        print("Interactive CLI requires a TTY. Use --help or pass explicit command flags.")
        return 2

    init_environment()
    demo = parsed_args.demo
    if os.environ.get("OBD_CLI_TRACE") == "1":
        print(
            f"[OBD_CLI_TRACE] calling run_cli pid={os.getpid()} demo={demo}",
            file=sys.stderr,
        )
    run_cli(demo=demo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
