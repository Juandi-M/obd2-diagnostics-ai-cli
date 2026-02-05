from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PRESENTATION_DIR = ROOT / "app" / "presentation"
APPLICATION_DIR = ROOT / "app" / "application"
QT_DIR = PRESENTATION_DIR / "qt"
QT_VIEWMODELS_DIR = QT_DIR / "viewmodels"

RULES = [
    {
        "name": "presentation_infrastructure_import",
        "paths": [PRESENTATION_DIR],
        "deny_pattern": re.compile(r"\bapp\.infrastructure\b"),
        "allow_paths": set(),
    },
    {
        "name": "presentation_obd_import",
        "paths": [PRESENTATION_DIR],
        "deny_pattern": re.compile(r"\bfrom\s+obd\b|\bimport\s+obd\b|\bobd\."),
        "allow_paths": set(),
    },
    {
        "name": "application_obd_import",
        "paths": [APPLICATION_DIR],
        "deny_pattern": re.compile(r"\bfrom\s+obd\b|\bimport\s+obd\b|\bobd\."),
        "allow_paths": set(),
    },
    {
        "name": "qt_view_import_use_cases",
        "paths": [QT_DIR],
        "deny_pattern": re.compile(r"\bapp\.application\.use_cases\b|\bapp\.application\.vehicle\b"),
        "allow_paths": {QT_VIEWMODELS_DIR},
    },
    {
        "name": "application_imports_presentation",
        "paths": [APPLICATION_DIR],
        "deny_pattern": re.compile(r"\bapp\.presentation\b"),
        "allow_paths": set(),
    },
    {
        "name": "tools_import_app",
        "paths": [ROOT / "tools"],
        "deny_pattern": re.compile(r"^\s*(from|import)\s+app\b"),
        "allow_paths": set(),
    },
]


def _iter_py_files(base: Path):
    for path in base.rglob("*.py"):
        if path.name == "__pycache__":
            continue
        yield path


def _is_under(path: Path, parents: set[Path]) -> bool:
    for parent in parents:
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            continue
    return False


def main() -> int:
    violations: list[tuple[str, Path, int, str]] = []
    for rule in RULES:
        deny = rule["deny_pattern"]
        allow = rule["allow_paths"]
        for base in rule["paths"]:
            for path in _iter_py_files(base):
                if allow and _is_under(path, allow):
                    continue
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
                for idx, line in enumerate(lines, start=1):
                    if deny.search(line):
                        violations.append((rule["name"], path, idx, line.strip()))
    if violations:
        print("Architecture guard violations:")
        for name, path, line_no, line in violations:
            rel = path.relative_to(ROOT)
            print(f"- {name}: {rel}:{line_no}: {line}")
        return 1
    print("Architecture guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
