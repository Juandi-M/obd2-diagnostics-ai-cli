from __future__ import annotations

import re
from typing import List

_HEX_RE = re.compile(r"^[0-9A-F]+$")


def strip_noise(lines: List[str]) -> List[str]:
    """
    El ELM puede meter ruido tipo: SEARCHING..., BUS INIT..., etc.
    Removemos lo obvio pero sin destruir payload.
    """
    drop_prefix = (
        "SEARCHING",
        "BUS INIT",
        "STOPPED",
        "OK",
        "ELM",
    )
    cleaned: List[str] = []
    for ln in lines:
        up = ln.strip().upper()
        if not up:
            continue
        if any(up.startswith(x) for x in drop_prefix):
            continue
        if up in (">", "?"):
            continue
        cleaned.append(ln.strip())
    return cleaned


def extract_hex_blob(lines: List[str]) -> str:
    """
    Une líneas y deja solo hex (tolerante a headers/texto).
    """
    up = " ".join(lines).upper()
    return "".join(ch for ch in up if ch in "0123456789ABCDEF")


def looks_like_hex(hex_blob: str) -> bool:
    return bool(hex_blob) and (_HEX_RE.match(hex_blob) is not None)


def matches_probe_pattern(probe: str, hex_blob: str) -> bool:
    """
    Patrones mínimos “reales” por probe.
    """
    p = probe.strip().upper()
    if p == "0100":
        return "4100" in hex_blob and len(hex_blob) >= 12
    if p == "010C":
        return "410C" in hex_blob and len(hex_blob) >= 10
    if p == "0105":
        return "4105" in hex_blob and len(hex_blob) >= 10
    if p == "0902":
        return "4902" in hex_blob and len(hex_blob) >= 10

    # probe desconocido: con que haya hex razonable
    return looks_like_hex(hex_blob) and len(hex_blob) >= 8


def probe_ok(probe: str, raw_lines: List[str]) -> bool:
    """
    Evalúa un probe usando:
    - limpieza de ruido
    - extracción de hex
    - match por patrón
    - filtro rápido de errores textuales
    """
    up = " ".join(raw_lines).upper()
    if not raw_lines:
        return False
    if "NO DATA" in up or "UNABLE TO CONNECT" in up or "ERROR" in up or "DISCONNECTED" in up:
        return False

    cleaned = strip_noise(raw_lines)
    blob = extract_hex_blob(cleaned if cleaned else raw_lines)
    return matches_probe_pattern(probe, blob) or (looks_like_hex(blob) and len(blob) >= 10)
