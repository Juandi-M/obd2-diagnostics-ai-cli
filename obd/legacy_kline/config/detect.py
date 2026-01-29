from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from obd.elm.elm327 import ELM327
from obd.legacy_kline.config.apply import apply_profile
from obd.legacy_kline.config.errors import KLineContext, KLineDetectError
from obd.legacy_kline.profiles.base import KLineProfile
from obd.legacy_kline.runtime.policy import KLinePolicy, policy_for_profile
from obd.legacy_kline.runtime.routing import query_profile_report


@dataclass(frozen=True)
class ProbeAttempt:
    probe: str
    ok: bool
    query_summary: str
    lines_preview: List[str]


@dataclass(frozen=True)
class CandidateAttempt:
    profile_name: str
    family: str
    apply_ok: bool
    apply_error: Optional[str]
    verify_ok: bool
    verify_reason: str
    elapsed_ms: int
    probes: List[ProbeAttempt] = field(default_factory=list)


@dataclass(frozen=True)
class DetectReport:
    selected_profile: Optional[str]
    selected_reason: Optional[str]
    attempts: List[CandidateAttempt] = field(default_factory=list)

    def summary(self) -> str:
        if self.selected_profile:
            return f"Selected: {self.selected_profile} ({self.selected_reason})"
        if not self.attempts:
            return "No attempts"
        last = self.attempts[-1]
        return f"No profile matched. Last: {last.profile_name} -> {last.verify_reason}"


def _probe_ok_by_patterns(probe: str, lines: List[str]) -> bool:
    """
    Patrón mínimo por probe usando solo el texto raw.
    Mantenerlo simple: detectamos tokens hex con el marcador correcto.
    """
    up = " ".join(lines).upper()
    hex_blob = "".join(ch for ch in up if ch in "0123456789ABCDEF")

    p = probe.strip().upper()
    if p == "0100":
        return "4100" in hex_blob and len(hex_blob) >= 12
    if p == "010C":
        return "410C" in hex_blob and len(hex_blob) >= 10
    if p == "0105":
        return "4105" in hex_blob and len(hex_blob) >= 10
    if p == "0902":
        return "4902" in hex_blob and len(hex_blob) >= 10

    # probe desconocido: con que haya hex decente y no error textual
    if "NO DATA" in up or "UNABLE TO CONNECT" in up or "ERROR" in up:
        return False
    return len(hex_blob) >= 10


def detect_profile_report(
    elm: ELM327,
    candidates: List[KLineProfile],
    *,
    policy: Optional[KLinePolicy] = None,
) -> Tuple[KLineProfile, DetectReport]:
    """
    Detecta el mejor perfil probando candidatos:
    - apply_profile()
    - verify por probes con query_profile_report() (para evidencia real)

    Retorna (profile ganador, DetectReport)
    """
    if not candidates:
        raise KLineDetectError("No K-Line profile candidates provided")

    base_policy = policy or KLinePolicy()
    attempts: List[CandidateAttempt] = []

    last_reason = "unknown"
    for prof in candidates:
        start = time.monotonic()

        apply_ok = True
        apply_error: Optional[str] = None

        probes_detail: List[ProbeAttempt] = []
        verify_ok = False
        verify_reason = "not verified"

        try:
            apply_profile(elm, prof, reset_before_apply=True)
        except Exception as e:
            apply_ok = False
            apply_error = str(e)

        if apply_ok:
            # policy real por perfil (timeouts, warmup, extra delays, etc.)
            pol = policy_for_profile(prof, base=base_policy)

            # Ejecutamos probes, cada uno con reporte detallado
            for probe in (prof.verify_obd or ["0100"]):
                lines, qrep = query_profile_report(elm, probe, profile=prof, base_policy=pol)
                ok = _probe_ok_by_patterns(probe, lines)
                probes_detail.append(
                    ProbeAttempt(
                        probe=probe,
                        ok=ok,
                        query_summary=qrep.summary(),
                        lines_preview=lines[:3],
                    )
                )
                if ok:
                    verify_ok = True
                    verify_reason = f"OK: probe {probe} matched; {qrep.summary()}"
                    break

            if not verify_ok:
                verify_reason = f"All probes failed: {[p.probe for p in probes_detail]}"

        elapsed_ms = int((time.monotonic() - start) * 1000)

        attempts.append(
            CandidateAttempt(
                profile_name=prof.name,
                family=prof.family,
                apply_ok=apply_ok,
                apply_error=apply_error,
                verify_ok=verify_ok,
                verify_reason=verify_reason if apply_ok else f"apply failed: {apply_error}",
                elapsed_ms=elapsed_ms,
                probes=probes_detail,
            )
        )

        if verify_ok:
            report = DetectReport(
                selected_profile=prof.name,
                selected_reason=verify_reason,
                attempts=attempts,
            )
            return prof, report

        last_reason = attempts[-1].verify_reason

    report = DetectReport(
        selected_profile=None,
        selected_reason=None,
        attempts=attempts,
    )
    raise KLineDetectError(report.summary(), ctx=KLineContext(), cause=None)


def detect_profile(
    elm: ELM327,
    candidates: List[KLineProfile],
    *,
    policy: Optional[KLinePolicy] = None,
) -> Tuple[KLineProfile, str]:
    """
    Backwards-compatible:
    Retorna (profile ganador, reason).
    """
    prof, report = detect_profile_report(elm, candidates, policy=policy)
    return prof, report.selected_reason or report.summary()
