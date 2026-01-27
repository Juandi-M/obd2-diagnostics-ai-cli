from __future__ import annotations

import re
from typing import List

HEXISH_RE = re.compile(r"^[0-9A-Fa-f ]+$")

# Prefijos ruidosos típicos de ELM / adaptadores
NOISE_PREFIXES = (
    "SEARCHING",
    "BUS INIT",
    "UNABLE TO CONNECT",
    "STOPPED",
    "NO DATA",
    "CAN ERROR",
    "BUFFER FULL",
    "BUS BUSY",
    "BUS ERROR",
    "DATA ERROR",
)

def is_noise(line: str) -> bool:
    up = (line or "").strip().upper()
    if not up:
        return True

    # OK como línea suelta
    if up == "OK":
        return True

    # ELM327 version banners
    if up.startswith("ELM327"):
        return True

    return any(up.startswith(p) for p in NOISE_PREFIXES)

def normalize_tokens(line: str) -> List[str]:
    """
    Limpia una línea a solo hex y espacios, devuelve tokens uppercase.
    """
    if not line:
        return []
    clean = re.sub(r"[^0-9A-Fa-f ]", "", line)
    return [t.upper() for t in clean.split() if t]

def is_hexish_tokens(tokens: List[str]) -> bool:
    if not tokens:
        return False
    return bool(HEXISH_RE.match(" ".join(tokens)))
