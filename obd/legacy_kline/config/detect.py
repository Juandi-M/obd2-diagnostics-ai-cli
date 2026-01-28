from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from obd.elm.elm327 import ELM327
from obd.legacy_kline.config.apply import apply_profile
from obd.legacy_kline.config.errors import KLineContext, KLineDetectError
from obd.legacy_kline.config.verify import verify_profile
from obd.legacy_kline.profiles.base import KLineProfile
from obd.legacy_kline.runtime.policy import KLinePolicy


@dataclass(frozen=True)
class CandidateAttempt:
    profile_name: str
    family: str
    ok: bool
    reason: str
    elapsed_ms: int


@dataclass(frozen=True)
class DetectReport:
    selected_profile: Optional[str]
    attempts: List[CandidateAttempt] = field(default_factory=list)

    def summary(self) -> str:
        if self.selected_profile:
            return f"Selected: {self.selected_profile}"
        if not self.attempts:
            return "No attempts"
        last = self.attempts[-1]
        return f"No profile matched. Last: {last.profile_name} -> {last.reason}"


def detect_profile_report(
    elm: ELM327,
    candidates: List[KLineProfile],
    *,
    policy: Optional[KLinePolicy] = None,
) -> Tuple[KLineProfile, DetectReport]:
    """
    Igual que detect_profile, pero retorna reporte detallado.
    """
    if not candidates:
        raise KLineDetectError("No K-Line profile candidates provided")

    pol = policy or KLinePolicy()
    attempts: List[CandidateAttempt] = []

    for prof in candidates:
        start = time.monotonic()
        ok = False
        reason = ""
        try:
            apply_profile(elm, prof, reset_before_apply=True)
            ok, reason = verify_profile(elm, prof, policy=pol)
        except Exception as e:
            ok = False
            reason = f"exception: {e}"

        elapsed_ms = int((time.monotonic() - start) * 1000)
        attempts.append(
            CandidateAttempt(
                profile_name=prof.name,
                family=prof.family,
                ok=ok,
                reason=reason,
                elapsed_ms=elapsed_ms,
            )
        )

        if ok:
            report = DetectReport(selected_profile=prof.name, attempts=attempts)
            return prof, report

    report = DetectReport(selected_profile=None, attempts=attempts)
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
    # reason = último attempt OK
    last_ok = next((a for a in reversed(report.attempts) if a.ok), None)
    reason = last_ok.reason if last_ok else report.summary()
    return prof, reason
