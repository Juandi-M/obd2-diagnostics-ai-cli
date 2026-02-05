from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class KLineContext:
    profile_name: Optional[str] = None
    at_or_obd_command: Optional[str] = None
    lines: Optional[List[str]] = None


class KLineError(Exception):
    """
    Base exception para protocolo legado K-Line.
    Incluye contexto útil para debugging.
    """

    def __init__(self, message: str, *, ctx: Optional[KLineContext] = None, cause: Exception | None = None):
        super().__init__(message)
        self.ctx = ctx
        self.cause = cause

    def __str__(self) -> str:
        base = super().__str__()
        extra = []
        if self.ctx:
            if self.ctx.profile_name:
                extra.append(f"profile={self.ctx.profile_name}")
            if self.ctx.at_or_obd_command:
                extra.append(f"cmd={self.ctx.at_or_obd_command}")
            if self.ctx.lines:
                preview = self.ctx.lines[:3]
                extra.append(f"lines={preview}")
        if extra:
            base += " [" + " | ".join(extra) + "]"
        return base


class KLineProfileError(KLineError):
    pass


class KLineApplyError(KLineError):
    pass


class KLineVerifyError(KLineError):
    pass


class KLineDetectError(KLineError):
    pass
