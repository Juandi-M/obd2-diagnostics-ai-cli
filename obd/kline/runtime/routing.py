from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional

from obd.elm.elm327 import ELM327
from obd.kline.profiles.base import KLineProfile
from obd.kline.runtime.policy import KLinePolicy, policy_for_profile
from obd.kline.runtime.quirks import (
    QuirkSet,
    QUIRK_RETRY_ON_NO_DATA,
    QUIRK_IGNORE_UNABLE_TO_CONNECT,
    classify_response,
    is_retryable_response,
    response_is_hard_fail,
)


def _sleep(s: float) -> None:
    if s and s > 0:
        time.sleep(s)


def _normalize_at(cmd: str) -> str:
    cmd = cmd.strip()
    if not cmd:
        return cmd
    if cmd.upper().startswith("AT"):
        return cmd
    return f"AT {cmd}"


def send_at_lines(elm: ELM327, cmd: str, *, timeout_s: Optional[float] = None) -> List[str]:
    """
    Envía comando AT y devuelve líneas crudas.
    """
    cmd = _normalize_at(cmd)
    return elm.send_raw_lines(cmd, timeout=timeout_s)


def send_obd_lines(elm: ELM327, cmd: str, *, timeout_s: Optional[float] = None) -> List[str]:
    """
    Envía request OBD (ej: '0100') y devuelve líneas crudas.
    """
    cmd = cmd.strip().upper()
    return elm.send_raw_lines(cmd, timeout=timeout_s)


@dataclass(frozen=True)
class QueryAttempt:
    attempt: int
    elapsed_ms: int
    kind: str
    lines_preview: List[str]


@dataclass(frozen=True)
class QueryReport:
    cmd: str
    attempts: List[QueryAttempt]

    def summary(self) -> str:
        if not self.attempts:
            return "No attempts"
        last = self.attempts[-1]
        return f"{self.cmd}: last={last.kind} lines={last.lines_preview}"


def _do_warmup(
    elm: ELM327,
    *,
    policy: KLinePolicy,
    quirks: QuirkSet,
    timeout_s: float,
) -> None:
    """
    Warmup probe: ayuda cuando el ECU “está dormido” o el init tarda en estabilizar.
    """
    if not policy.warmup_enabled:
        return

    retry_on_no_data = quirks.enabled(QUIRK_RETRY_ON_NO_DATA, default=False)
    ignore_no_connect = quirks.enabled(QUIRK_IGNORE_UNABLE_TO_CONNECT, default=False)

    for _ in range(max(1, policy.warmup_attempts)):
        lines = send_obd_lines(elm, policy.warmup_probe, timeout_s=timeout_s)
        if response_is_hard_fail(lines):
            return
        kind = classify_response(lines)
        if kind == "ok":
            _sleep(policy.warmup_delay_s)
            return
        if not is_retryable_response(lines, retry_on_no_data=retry_on_no_data, ignore_unable_to_connect=ignore_no_connect):
            return
        _sleep(policy.inter_request_delay_s)


def query_with_policy(
    elm: ELM327,
    cmd: str,
    *,
    policy: KLinePolicy,
    timeout_s: Optional[float] = None,
) -> List[str]:
    """
    Query con policy (retries/delays/backoff).
    Retorna líneas crudas de la última respuesta (o la primera "ok" si aparece).
    """
    t = timeout_s if timeout_s is not None else policy.timeout_s
    last_lines: List[str] = []

    # settle inicial
    _sleep(policy.initial_settle_delay_s)

    # warmup (si aplica)
    # Nota: aquí no hay profile; se usa el policy tal cual. Si quieres warmup por profile,
    # llama query_profile() abajo.
    # (config/verify ya usa policy_for_profile(profile) si lo deseas)
    # -> Dejamos warmup en query_profile().
    for attempt in range(policy.retries + 1):
        start = time.monotonic()
        last_lines = send_obd_lines(elm, cmd, timeout_s=t)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        if response_is_hard_fail(last_lines):
            return last_lines

        up_kind = classify_response(last_lines)

        # Si está OK, devolvemos inmediatamente.
        if up_kind == "ok":
            return last_lines

        # Delay entre requests
        _sleep(policy.inter_request_delay_s)

        # Backoff incremental si hay múltiples intentos
        if policy.backoff_s > 0:
            _sleep(policy.backoff_s * attempt)

    return last_lines


def query_profile(
    elm: ELM327,
    cmd: str,
    *,
    profile: KLineProfile,
    base_policy: Optional[KLinePolicy] = None,
    timeout_s: Optional[float] = None,
) -> List[str]:
    """
    Query “producto”: toma profile + base_policy y aplica quirks reales (retry_on_no_data, warmup, etc.)
    """
    pol = policy_for_profile(profile, base=base_policy)
    qs = QuirkSet.from_profile_dict(profile.quirks)
    t = timeout_s if timeout_s is not None else pol.timeout_s

    retry_on_no_data = qs.enabled(QUIRK_RETRY_ON_NO_DATA, default=False)
    ignore_no_connect = qs.enabled(QUIRK_IGNORE_UNABLE_TO_CONNECT, default=False)

    # settle inicial
    _sleep(pol.initial_settle_delay_s)

    # warmup probe si corresponde
    _do_warmup(elm, policy=pol, quirks=qs, timeout_s=t)

    last_lines: List[str] = []
    for attempt in range(pol.retries + 1):
        start = time.monotonic()
        last_lines = send_obd_lines(elm, cmd, timeout_s=t)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        if response_is_hard_fail(last_lines):
            return last_lines

        kind = classify_response(last_lines)

        # éxito
        if kind == "ok":
            return last_lines

        # ¿retry?
        if not is_retryable_response(last_lines, retry_on_no_data=retry_on_no_data, ignore_unable_to_connect=ignore_no_connect):
            return last_lines

        # delays
        _sleep(pol.inter_request_delay_s)
        if pol.backoff_s > 0:
            _sleep(pol.backoff_s * attempt)

    return last_lines


def query_profile_report(
    elm: ELM327,
    cmd: str,
    *,
    profile: KLineProfile,
    base_policy: Optional[KLinePolicy] = None,
    timeout_s: Optional[float] = None,
) -> tuple[List[str], QueryReport]:
    """
    Igual que query_profile, pero devuelve reporte de intentos (para debug/telemetría).
    """
    pol = policy_for_profile(profile, base=base_policy)
    qs = QuirkSet.from_profile_dict(profile.quirks)
    t = timeout_s if timeout_s is not None else pol.timeout_s

    retry_on_no_data = qs.enabled(QUIRK_RETRY_ON_NO_DATA, default=False)
    ignore_no_connect = qs.enabled(QUIRK_IGNORE_UNABLE_TO_CONNECT, default=False)

    attempts: List[QueryAttempt] = []

    _sleep(pol.initial_settle_delay_s)
    _do_warmup(elm, policy=pol, quirks=qs, timeout_s=t)

    last_lines: List[str] = []
    for attempt in range(pol.retries + 1):
        start = time.monotonic()
        last_lines = send_obd_lines(elm, cmd, timeout_s=t)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        kind = classify_response(last_lines)
        attempts.append(
            QueryAttempt(
                attempt=attempt,
                elapsed_ms=elapsed_ms,
                kind=kind,
                lines_preview=last_lines[:3],
            )
        )

        if response_is_hard_fail(last_lines):
            return last_lines, QueryReport(cmd=cmd, attempts=attempts)

        if kind == "ok":
            return last_lines, QueryReport(cmd=cmd, attempts=attempts)

        if not is_retryable_response(last_lines, retry_on_no_data=retry_on_no_data, ignore_unable_to_connect=ignore_no_connect):
            return last_lines, QueryReport(cmd=cmd, attempts=attempts)

        _sleep(pol.inter_request_delay_s)
        if pol.backoff_s > 0:
            _sleep(pol.backoff_s * attempt)

    return last_lines, QueryReport(cmd=cmd, attempts=attempts)
