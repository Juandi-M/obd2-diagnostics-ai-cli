from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from obd.elm.elm327 import ELM327
from obd.kline.config.detect import detect_profile_report, DetectReport
from obd.kline.profiles.base import KLineProfile
from obd.kline.runtime.policy import KLinePolicy
from obd.kline.runtime.routing import query_profile


@dataclass(frozen=True)
class SessionInfo:
    profile_name: str
    family: str
    reason: str


class KLineSession:
    """
    API de sesión para que el CLI/UI no toque config/runtime directo.

    Flujo típico:
      - session = KLineSession.auto(elm, candidates=td5_candidates())
      - scanner = KLineScanner(session)
      - scanner.live_basic() / scanner.read_dtcs()
    """

    def __init__(
        self,
        elm: ELM327,
        *,
        profile: KLineProfile,
        policy: Optional[KLinePolicy] = None,
        detect_report: Optional[DetectReport] = None,
        reason: str = "",
    ):
        self.elm = elm
        self.profile = profile
        self.policy = policy or KLinePolicy()
        self.detect_report = detect_report
        self.reason = reason

    @classmethod
    def auto(
        cls,
        elm: ELM327,
        *,
        candidates: Sequence[KLineProfile],
        policy: Optional[KLinePolicy] = None,
    ) -> "KLineSession":
        """
        Detecta perfil automáticamente usando detect_profile_report().
        """
        prof, rep = detect_profile_report(elm, list(candidates), policy=policy)
        reason = rep.selected_reason or rep.summary()
        return cls(elm, profile=prof, policy=policy, detect_report=rep, reason=reason)

    @property
    def info(self) -> SessionInfo:
        return SessionInfo(
            profile_name=self.profile.name,
            family=self.profile.family,
            reason=self.reason,
        )

    def query_lines(self, cmd: str) -> List[str]:
        """
        Ejecuta query OBD (ej: '0100', '03', '0902') con quirks/policy del profile.
        """
        return query_profile(self.elm, cmd, profile=self.profile, base_policy=self.policy)

    def query_hex(self, cmd: str) -> str:
        """
        Ejecuta query_lines y devuelve hex-only concatenado (como tu send_obd()).
        """
        lines = self.query_lines(cmd)
        up = " ".join(lines).upper()
        return "".join(ch for ch in up if ch in "0123456789ABCDEF")

    def close(self) -> None:
        """
        Conveniencia: cierra el ELM si querés que la sesión lo controle.
        """
        try:
            self.elm.close()
        except Exception:
            pass
