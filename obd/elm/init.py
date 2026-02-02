# obd/elm/init.py
from __future__ import annotations

import re
from typing import Optional, TYPE_CHECKING

from .errors import CommunicationError

if TYPE_CHECKING:
    from .elm327 import ELM327


def extract_version(response: str) -> Optional[str]:
    s = (response or "").strip()
    if not s:
        return None
    m = re.search(r"(ELM327\s*v?\s*[\w\.]+)", s, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return s[:40].strip() if s else None


def initialize_elm(elm: "ELM327") -> bool:
    """
    Performs AT init. Returns True/False (never throws up to connect()).
    """
    try:
        resp_lines = elm.send_raw_lines("ATZ", timeout=2.0)
        resp = "\n".join(resp_lines)
        elm.elm_version = extract_version(resp) or "unknown"

        # Basic config
        elm.send_raw_lines("ATE0", timeout=1.0)  # echo off
        elm.send_raw_lines("ATL0", timeout=1.0)  # linefeeds off

        # Spaces ON if headers are ON, because parser tokenizes by spaces
        elm.send_raw_lines("ATS1" if elm.headers_on else "ATS0", timeout=1.0)

        # Headers
        elm.send_raw_lines("ATH1" if elm.headers_on else "ATH0", timeout=1.0)

        # Timing + protocol auto
        elm.send_raw_lines("ATAT1", timeout=1.0)
        elm.send_raw_lines("ATSP0", timeout=1.0)

        # Allow long messages if supported
        try:
            elm.send_raw_lines("ATAL", timeout=1.0)
        except CommunicationError:
            pass

        return True
    except Exception:
        return False
