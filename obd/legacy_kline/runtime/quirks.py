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
    Flags/params para workarounds.
    Por ahora usamos flags (bool). params queda listo para tuning futuro.
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


def classify_response(lines: list[str]) -> str:
    if not lines:
        return "empty"

    up = " ".join(lines).upper()

    if "NO DATA" in up:
        return "no_data"
    if "UNABLE TO CONNECT" in up:
        return "no_connect"
    if "DISCONNECTED" in up:
        return "error"
    if "ERROR" in up:
        return "error"
    if "?" in up:
        return "invalid"

    # Heurística: si no hay casi hex, no es respuesta real
    hex_blob = "".join(ch for ch in up if ch in "0123456789ABCDEF")
    if len(hex_blob) < 6:
        return "invalid"

    return "ok"


def is_retryable_response(
    lines: list[str],
    *,
    retry_on_no_data: bool,
    ignore_unable_to_connect: bool,
) -> bool:
    """
    Aquí quedó FIX:
    - no_connect (UNABLE TO CONNECT) por defecto NO retry (para no perder tiempo)
    - pero si el quirk ignore_unable_to_connect está ON, entonces sí retry.
    """
    kind = classify_response(lines)

    if kind in ("empty", "error", "invalid"):
        return True

    if kind == "no_data":
        return retry_on_no_data

    if kind == "no_connect":
        return bool(ignore_unable_to_connect)

    return False


def response_is_hard_fail(lines: list[str]) -> bool:
    up = " ".join(lines).upper()
    if "DISCONNECTED" in up:
        return True
    return False
