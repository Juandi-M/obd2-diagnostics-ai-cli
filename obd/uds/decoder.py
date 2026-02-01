from __future__ import annotations

from typing import Any, Dict


def decode_ascii(data: bytes) -> str:
    return data.decode("ascii", errors="ignore").strip()


def decode_uint(data: bytes) -> int:
    value = 0
    for b in data:
        value = (value << 8) | b
    return value


def decode_hex(data: bytes) -> str:
    return data.hex().upper()


def decode_did_value(entry: Dict[str, Any], data: bytes) -> Any:
    decoder = (entry.get("decoder") or "hex").lower()
    if decoder == "ascii":
        return decode_ascii(data)
    if decoder == "uint":
        return decode_uint(data)
    return decode_hex(data)
