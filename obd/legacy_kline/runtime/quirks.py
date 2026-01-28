from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


# Quirk keys (convención)
QUIRK_FORCE_HEADERS_ON = "force_headers_on"
QUIRK_FORCE_HEADERS_OFF = "force_headers_off"
QUIRK_EXTRA_INTER_REQUEST_DELAY = "extra_inter_request_delay"
QUIRK_EXTRA_INTER_COMMAND_DELAY = "extra_inter_command_delay"
QUIRK_RETRY_ON_NO_DATA = "retry_on_no_data"
QUIRK_IGNORE_UNABLE_TO_CONNECT = "ignore_unable_to_connect"
QUIRK_REQUIRE_WARMUP_PROBE = "require_warmup_probe"


@dataclass(frozen=True)
class QuirkSet:
    """
    Conjunto de flags/parametros para workarounds K-Line.
    Puedes guardarlo como dict en profile.quirks, pero esta clase ayuda a tiparlo.
    """
    flags: Dict[str, bool]
    params: Dict[str, float]

    @staticmethod
    def from_profile_dict(d: Optional[Dict[str, bool]]) -> "QuirkSet":
        return QuirkSet(flags=d or {}, params={})

    def enabled(self, key: str, default: bool = False) -> bool:
        return bool(self.flags.get(key, default))

    def param(self, key: str, default: float = 0.0) -> float:
        return float(self.params.get(key, default))


def is_retryable_response(lines: list[str], *, retry_on_no_data: bool) -> bool:
    up = " ".join(lines).upper()
    if not lines:
        return True
    if "ERROR" in up:
        return True
    if "UNABLE TO CONNECT" in up:
        return True
    if retry_on_no_data and "NO DATA" in up:
        return True
    return False


def response_is_hard_fail(lines: list[str]) -> bool:
    """
    'Hard fail' = no vale la pena seguir (ej. adaptador muerto).
    Por ahora conservador.
    """
    up = " ".join(lines).upper()
    if "DISCONNECTED" in up:
        return True
    return False
