from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def _normalize(command: str) -> str:
    return "".join(command.strip().split()).upper()


def _parse_log(path: Path) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    pattern = re.compile(r"^\\[(.*?)\\]\\s+(TX|RX)\\s+(.*)$")
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.rstrip()
        match = pattern.match(line)
        if match:
            if current:
                entries.append(current)
            current = {
                "direction": match.group(2),
                "command": match.group(3).strip(),
                "lines": [],
            }
            continue
        if current and line.startswith("  "):
            current["lines"].append(line.strip())
    if current:
        entries.append(current)
    return entries


def _filter_entries(
    entries: List[Dict[str, Any]],
    *,
    rx_only: bool,
    include: List[str],
    exclude: List[str],
) -> List[Dict[str, Any]]:
    include_norm = [_normalize(item) for item in include]
    exclude_norm = [_normalize(item) for item in exclude]

    def allowed(command: str) -> bool:
        norm = _normalize(command)
        if include_norm and not any(norm.startswith(prefix) for prefix in include_norm):
            return False
        if exclude_norm and any(norm.startswith(prefix) for prefix in exclude_norm):
            return False
        return True

    filtered: List[Dict[str, Any]] = []
    for entry in entries:
        if rx_only and entry.get("direction") != "RX":
            continue
        if not allowed(entry.get("command", "")):
            continue
        filtered.append(entry)
    return filtered


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert obd_raw.log into replay fixtures")
    parser.add_argument("--input", required=True, help="Path to obd_raw.log")
    parser.add_argument("--output", required=True, help="Output fixture JSON path")
    parser.add_argument("--headers-on", action="store_true", help="Set meta.headers_on true")
    parser.add_argument("--headers-off", action="store_true", help="Set meta.headers_on false")
    parser.add_argument("--elm-version", default="", help="Set meta.elm_version")
    parser.add_argument("--protocol", default="", help="Set meta.protocol")
    parser.add_argument("--manufacturer", default="", help="Set meta.manufacturer")
    parser.add_argument("--expected", default="", help="Path to JSON with expected outputs")
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Keep only commands with this prefix (repeatable)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Drop commands with this prefix (repeatable)",
    )
    parser.add_argument(
        "--keep-tx",
        action="store_true",
        help="Include TX entries as steps (default uses RX only)",
    )

    args = parser.parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    entries = _parse_log(input_path)
    entries = _filter_entries(
        entries,
        rx_only=not args.keep_tx,
        include=args.include,
        exclude=args.exclude,
    )
    steps = [
        {"command": entry.get("command", ""), "lines": entry.get("lines", [])}
        for entry in entries
    ]

    meta: Dict[str, Any] = {}
    if args.headers_on:
        meta["headers_on"] = True
    if args.headers_off:
        meta["headers_on"] = False
    if args.elm_version:
        meta["elm_version"] = args.elm_version
    if args.protocol:
        meta["protocol"] = args.protocol
    if args.manufacturer:
        meta["manufacturer"] = args.manufacturer

    expected: Dict[str, Any] = {}
    if args.expected:
        expected_path = Path(args.expected)
        expected = json.loads(expected_path.read_text(encoding="utf-8"))

    payload = {
        "meta": meta,
        "steps": steps,
        "expected": expected,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
