from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .normalize import is_noise, normalize_tokens, is_hexish_tokens
from .payload import payload_from_tokens

def group_by_ecu(lines: List[str], headers_on: bool = True) -> Dict[str, List[List[str]]]:
    """
    Retorna:
      ecu -> [ [tokens_line1], [tokens_line2], ... ]
    """
    out: Dict[str, List[List[str]]] = {}
    for ln in lines or []:
        if not ln:
            continue
        if is_noise(ln):
            continue

        tokens = normalize_tokens(ln)
        if not tokens or not is_hexish_tokens(tokens):
            continue

        if headers_on:
            ecu = tokens[0]
            out.setdefault(ecu, []).append(tokens)
        else:
            out.setdefault("NOHDR", []).append(tokens)
    return out

def merge_payloads(grouped: Dict[str, List[List[str]]], headers_on: bool = True) -> Dict[str, List[str]]:
    """
    Aplana todas las líneas por ECU en un solo payload (lista de tokens hex).
    """
    merged: Dict[str, List[str]] = {}
    for ecu, msgs in (grouped or {}).items():
        out: List[str] = []
        for msg in msgs:
            out.extend(payload_from_tokens(msg, headers_on=headers_on))
        merged[ecu] = out
    return merged

def find_obd_response_payload(
    merged_payloads: Dict[str, List[str]],
    expected_prefix: List[str],
    prefer_ecus: Optional[List[str]] = None,
) -> Optional[Tuple[str, List[str]]]:
    """
    Busca el ECU cuyo payload contenga el prefijo esperado (ej: ["41","0C"]).
    Retorna (ecu, payload_desde_prefix) o None
    """
    if not merged_payloads or not expected_prefix:
        return None

    ecu_order = list(merged_payloads.keys())

    if prefer_ecus:
        preferred = [e for e in prefer_ecus if e in merged_payloads]
        rest = [e for e in ecu_order if e not in preferred]
        ecu_order = preferred + rest

    n = len(expected_prefix)
    for ecu in ecu_order:
        payload = merged_payloads.get(ecu, [])
        if len(payload) < n:
            continue
        for i in range(0, len(payload) - n + 1):
            if payload[i : i + n] == expected_prefix:
                return ecu, payload[i:]
    return None
