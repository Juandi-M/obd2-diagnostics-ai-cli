from __future__ import annotations

import re
from typing import List

VIN_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")  # excluye I,O,Q

def extract_ascii_from_hex_tokens(tokens: List[str]) -> str:
    s = ""
    for t in tokens or []:
        try:
            b = int(t, 16)
        except Exception:
            continue
        if 32 <= b <= 126:
            s += chr(b)
    return s

def is_valid_vin(vin: str) -> bool:
    vin = (vin or "").strip().upper()
    return bool(VIN_RE.match(vin))
