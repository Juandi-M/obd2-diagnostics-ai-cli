from __future__ import annotations

import time
from typing import List, Optional

from obd.elm.elm327 import ELM327
from obd.legacy_kline.runtime.policy import KLinePolicy


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


def query_with_policy(
    elm: ELM327,
    cmd: str,
    *,
    policy: KLinePolicy,
    timeout_s: Optional[float] = None,
) -> List[str]:
    """
    Query con retry básico.
    """
    t = timeout_s if timeout_s is not None else policy.timeout_s
    last_lines: List[str] = []

    for attempt in range(policy.retries + 1):
        if attempt == 0 and policy.initial_settle_delay_s > 0:
            time.sleep(policy.initial_settle_delay_s)

        last_lines = send_obd_lines(elm, cmd, timeout_s=t)

        # Pequeño delay entre requests
        if policy.inter_request_delay_s > 0:
            time.sleep(policy.inter_request_delay_s)

        # Heurística simple: si hay respuesta útil, salimos
        up = " ".join(last_lines).upper()
        if last_lines and ("NO DATA" not in up) and ("UNABLE TO CONNECT" not in up) and ("ERROR" not in up):
            return last_lines

    return last_lines
