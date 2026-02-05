from __future__ import annotations

from typing import List, Tuple

from obd.elm.elm327 import ELM327
from obd.kline.config.errors import KLineContext, KLineVerifyError
from obd.kline.profiles.base import KLineProfile
from obd.kline.runtime.policy import KLinePolicy
from obd.kline.runtime.routing import query_profile
from obd.kline.runtime.probes import probe_ok, strip_noise, extract_hex_blob


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

            if probe_ok(probe, raw_lines):
                cleaned = strip_noise(raw_lines)
                blob = extract_hex_blob(cleaned if cleaned else raw_lines)
                return True, f"OK: probe {probe} matched; lines={raw_lines[:3]} hex={blob[:24]}"

        return False, f"All probes failed: {probes}"

    except Exception as e:
        raise KLineVerifyError(
            "Verify failed",
            ctx=KLineContext(profile_name=profile.name),
            cause=e,
        ) from e
