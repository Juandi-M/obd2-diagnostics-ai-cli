from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

from obd.elm.elm327 import ELM327
from obd.legacy_kline.config.errors import KLineContext, KLineVerifyError
from obd.legacy_kline.profiles.base import KLineProfile
from obd.legacy_kline.runtime.policy import KLinePolicy
from obd.legacy_kline.runtime.routing import query_profile


_HEX_RE = re.compile(r"^[0-9A-F]+$")


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    reason: str
    probe: str
    lines_preview: List[str]
    hex_preview: str


def _strip_noise(lines: List[str]) -> List[str]:
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
        # si es solo el prompt o un '?' suelto, fuera
        if up in (">", "?"):
            continue
        cleaned.append(ln.strip())
    return cleaned


def _extract_hex_blob(lines: List[str]) -> str:
    """
    Une líneas y deja solo hex (tolerante a headers/texto).
    """
    up = " ".join(lines).upper()
    hex_only = "".join(ch for ch in up if ch in "0123456789ABCDEF")
    return hex_only


def _looks_like_hex(hex_blob: str) -> bool:
    return bool(hex_blob) and _HEX_RE.match(hex_blob) is not None


def _matches_probe_pattern(probe: str, hex_blob: str) -> bool:
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
    # probes desconocidos: con que haya hex razonable
    return _looks_like_hex(hex_blob) and len(hex_blob) >= 8


def verify_profile(
    elm: ELM327,
    profile: KLineProfile,
    *,
    policy: KLinePolicy,
) -> Tuple[bool, str]:
    """
    Verifica que el perfil realmente logra hablar con el vehículo.
    Devuelve (ok, reason).

    IMPORTANTE: Usa query_profile() => aplica quirks/policy/warmup real.
    """
    probes = profile.verify_obd or ["0100"]

    try:
        for probe in probes:
            raw_lines = query_profile(elm, probe, profile=profile, base_policy=policy)
            up_join = " ".join(raw_lines).upper()

            # Fails claros (hard)
            if "DISCONNECTED" in up_join:
                return False, "ELM disconnected"
            if "ERROR" in up_join:
                continue
            if "UNABLE TO CONNECT" in up_join:
                continue
            if "NO DATA" in up_join:
                continue

            cleaned = _strip_noise(raw_lines)
            hex_blob = _extract_hex_blob(cleaned if cleaned else raw_lines)

            # 1) match exacto por probe
            if _matches_probe_pattern(probe, hex_blob):
                return True, f"OK: probe {probe} matched pattern; lines={raw_lines[:3]}"

            # 2) fallback: si hay hex “real”, aceptamos pero lo marcamos como weak-ok
            if _looks_like_hex(hex_blob) and len(hex_blob) >= 10:
                return True, f"OK(weak): probe {probe} got hex; lines={raw_lines[:3]}"

        return False, f"All probes failed: {probes}"

    except Exception as e:
        raise KLineVerifyError(
            "Verify failed",
            ctx=KLineContext(profile_name=profile.name),
            cause=e,
        ) from e
