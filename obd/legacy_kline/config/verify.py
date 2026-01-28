from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

from obd.elm.elm327 import ELM327
from obd.legacy_kline.config.errors import KLineContext, KLineVerifyError
from obd.legacy_kline.profiles.base import KLineProfile
from obd.legacy_kline.runtime.policy import KLinePolicy
from obd.legacy_kline.runtime.routing import query_with_policy


_HEX_RE = re.compile(r"^[0-9A-F]+$")


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    reason: str
    probe: str
    lines_preview: List[str]


def _strip_noise(lines: List[str]) -> List[str]:
    """
    El ELM puede meter líneas “humanas”: BUS INIT..., SEARCHING..., etc.
    Removemos las obvias, pero no destruimos payload.
    """
    drop = ("SEARCHING", "BUS INIT", "STOPPED", "OK", "ELM", ">", "?")
    cleaned: List[str] = []
    for ln in lines:
        up = ln.strip().upper()
        if not up:
            continue
        if any(up.startswith(x) for x in drop):
            continue
        cleaned.append(ln.strip())
    return cleaned


def _extract_hex_blob(lines: List[str]) -> str:
    """
    Une líneas y deja solo hex (como send_obd hace, pero aquí toleramos headers/texto).
    """
    up = " ".join(lines).upper()
    # quita todo excepto hex
    hex_only = "".join(ch for ch in up if ch in "0123456789ABCDEF")
    return hex_only


def _looks_like_mode01_0100(hex_blob: str) -> bool:
    # Respuesta típica: 4100 + 4 bytes de bitmask + ...
    # Solo exigimos que aparezca 4100 y al menos 8-10 hex más.
    return "4100" in hex_blob and len(hex_blob) >= 12


def _looks_like_mode09_vin(hex_blob: str) -> bool:
    # VIN: 4902 ... (a veces multi-frame, pero al menos 4902 debe aparecer)
    return "4902" in hex_blob and len(hex_blob) >= 10


def _looks_like_any_obd_response(hex_blob: str) -> bool:
    # Heurística mínima: debe tener al menos 6 hex chars y no ser pura basura
    return len(hex_blob) >= 6 and _HEX_RE.match(hex_blob) is not None


def verify_profile(elm: ELM327, profile: KLineProfile, *, policy: KLinePolicy) -> Tuple[bool, str]:
    """
    Verifica que el perfil logra hablar con el vehículo con probes.
    Devuelve (ok, reason).
    """
    probes = profile.verify_obd or ["0100"]
    try:
        for probe in probes:
            raw_lines = query_with_policy(elm, probe, policy=policy, timeout_s=profile.request_timeout_s)
            cleaned = _strip_noise(raw_lines)
            hex_blob = _extract_hex_blob(cleaned if cleaned else raw_lines)
            up_join = " ".join(raw_lines).upper()

            # Fails claros
            if "UNABLE TO CONNECT" in up_join:
                continue
            if "ERROR" in up_join:
                continue
            if "NO DATA" in up_join:
                continue

            # Checks por probe
            p = probe.strip().upper()
            if p == "0100" and _looks_like_mode01_0100(hex_blob):
                return True, f"OK: 0100 responded ({raw_lines[:3]})"
            if p == "0902" and _looks_like_mode09_vin(hex_blob):
                return True, f"OK: 0902 responded ({raw_lines[:3]})"

            # Fallback: cualquier respuesta OBD razonable
            if _looks_like_any_obd_response(hex_blob):
                return True, f"OK: probe {probe} got hex ({raw_lines[:3]})"

        return False, f"All probes failed: {probes}"

    except Exception as e:
        raise KLineVerifyError(
            "Verify failed",
            ctx=KLineContext(profile_name=profile.name),
            cause=e,
        ) from e
