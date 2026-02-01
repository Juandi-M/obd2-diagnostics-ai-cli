from __future__ import annotations

import sys

from app.flow import run_cli


def main() -> None:
    demo = len(sys.argv) > 1 and sys.argv[1] == "--demo"
    run_cli(demo=demo)


if __name__ == "__main__":
    main()
