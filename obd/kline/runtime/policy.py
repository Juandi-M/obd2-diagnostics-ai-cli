from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from obd.kline.profiles.base import KLineProfile
from obd.kline.runtime.quirks import (
    QuirkSet,
    QUIRK_EXTRA_INTER_REQUEST_DELAY,
    QUIRK_REQUIRE_WARMUP_PROBE,
)


@dataclass(frozen=True)
class KLinePolicy:
    """
    Policy runtime para K-Line:
    - retries: número de reintentos adicionales (total intentos = retries + 1)
    - timeout_s: timeout por request (si no se pasa override)
    - inter_request_delay_s: delay entre requests (ayuda a ECUs sensibles)
    - initial_settle_delay_s: delay inicial antes del primer request (después de apply)
    - backoff_s: delay extra incremental por intento (0 = off)
    - warmup_enabled: si se hace warmup probe antes de probes “reales”
    - warmup_probe: comando OBD para calentar (default: "0100")
    - warmup_attempts: cuántas veces intentar warmup
    - warmup_delay_s: delay después de warmup
    """
    retries: int = 1
    timeout_s: float = 4.0

    inter_request_delay_s: float = 0.08
    initial_settle_delay_s: float = 0.12

    backoff_s: float = 0.05

    warmup_enabled: bool = False
    warmup_probe: str = "0100"
    warmup_attempts: int = 1
    warmup_delay_s: float = 0.10

    def with_overrides(
        self,
        *,
        retries: Optional[int] = None,
        timeout_s: Optional[float] = None,
        inter_request_delay_s: Optional[float] = None,
        initial_settle_delay_s: Optional[float] = None,
        backoff_s: Optional[float] = None,
        warmup_enabled: Optional[bool] = None,
        warmup_probe: Optional[str] = None,
        warmup_attempts: Optional[int] = None,
        warmup_delay_s: Optional[float] = None,
    ) -> "KLinePolicy":
        p = self
        if retries is not None:
            p = replace(p, retries=retries)
        if timeout_s is not None:
            p = replace(p, timeout_s=timeout_s)
        if inter_request_delay_s is not None:
            p = replace(p, inter_request_delay_s=inter_request_delay_s)
        if initial_settle_delay_s is not None:
            p = replace(p, initial_settle_delay_s=initial_settle_delay_s)
        if backoff_s is not None:
            p = replace(p, backoff_s=backoff_s)
        if warmup_enabled is not None:
            p = replace(p, warmup_enabled=warmup_enabled)
        if warmup_probe is not None:
            p = replace(p, warmup_probe=warmup_probe)
        if warmup_attempts is not None:
            p = replace(p, warmup_attempts=warmup_attempts)
        if warmup_delay_s is not None:
            p = replace(p, warmup_delay_s=warmup_delay_s)
        return p


def policy_for_profile(
    profile: KLineProfile,
    *,
    base: Optional[KLinePolicy] = None,
) -> KLinePolicy:
    """
    Construye una policy a partir de:
    - base policy
    - request_timeout_s del perfil
    - quirks del perfil
    """
    p = base or KLinePolicy()
    qs = QuirkSet.from_profile_dict(profile.quirks)

    # timeout por perfil
    p = p.with_overrides(timeout_s=profile.request_timeout_s)

    # si el perfil pide warmup explícito
    if qs.enabled(QUIRK_REQUIRE_WARMUP_PROBE, default=False):
        p = p.with_overrides(warmup_enabled=True, warmup_attempts=max(1, p.warmup_attempts))

    # extra delay entre requests
    if qs.enabled(QUIRK_EXTRA_INTER_REQUEST_DELAY, default=False):
        # subimos un poco el delay conservadoramente
        p = p.with_overrides(inter_request_delay_s=max(p.inter_request_delay_s, 0.12))

    return p
