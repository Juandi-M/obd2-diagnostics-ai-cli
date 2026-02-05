from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from app.application.state import AppState
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.utils.text import header_lines


def format_read_did(state: AppState, title_key: str, info: Dict[str, Any]) -> str:
    lines = header_lines(gui_t(state, title_key))
    lines.append(f"  DID: {info.get('did')}")
    if info.get("name"):
        lines.append(f"  Name: {info.get('name')}")
    lines.append(f"  Value: {info.get('value')}")
    lines.append(f"  Raw: {info.get('raw')}")
    return "\n".join(lines)


def format_send_raw(state: AppState, response: bytes) -> str:
    lines = header_lines(gui_t(state, "uds_send_raw"))
    lines.append(f"  {gui_t(state, 'uds_response')}: {response.hex().upper()}")
    return "\n".join(lines)


def format_read_dtcs(state: AppState, response: bytes) -> str:
    lines = header_lines(gui_t(state, "uds_read_dtcs"))
    if len(response) < 3 or response[0] != 0x59 or response[1] != 0x02:
        lines.append(f"  {gui_t(state, 'uds_response')}: {response.hex().upper()}")
        return "\n".join(lines)
    status_mask = response[2]
    payload = response[3:]
    if not payload:
        lines.append(f"  {gui_t(state, 'search_none')}")
        return "\n".join(lines)
    lines.append(f"  Status mask: 0x{status_mask:02X}")
    for idx in range(0, len(payload), 4):
        if idx + 4 > len(payload):
            break
        dtc_bytes = payload[idx : idx + 3]
        status = payload[idx + 3]
        lines.append(f"  - 0x{dtc_bytes.hex().upper()} | status 0x{status:02X}")
    return "\n".join(lines)


def format_cached_map(state: AppState, cached: Dict[str, Any]) -> str:
    modules = cached.get("modules") or []
    if not modules:
        return gui_t(state, "uds_discover_cached_none")
    lines = header_lines(gui_t(state, "uds_discover_cached"))
    proto = cached.get("protocol") or "?"
    addressing = cached.get("addressing") or "?"
    lines.append(f"  {gui_t(state, 'uds_discover_protocol')}: {proto} ({addressing})")
    for mod in modules:
        lines.append(f"\n  - TX {mod.get('tx_id')} -> RX {mod.get('rx_id')}")
        if mod.get("module_type"):
            lines.append(f"    {gui_t(state, 'uds_discover_type')}: {mod.get('module_type')}")
        fp = mod.get("fingerprint") or {}
        summary = fp.get("dtc_summary") or {}
        if summary:
            counts = " ".join(f"{k}:{v}" for k, v in summary.items())
            lines.append(f"    {gui_t(state, 'uds_discover_dtcs_summary')}: {counts}")
        if mod.get("responses"):
            lines.append(f"    {gui_t(state, 'uds_discover_responses')}: {', '.join(mod.get('responses'))}")
        if mod.get("requires_security"):
            lines.append(f"    {gui_t(state, 'uds_discover_security')}")
    return "\n".join(lines)


def _safe_join(values: Optional[Iterable[Any]]) -> str:
    if not values:
        return ""
    return ", ".join(str(v) for v in values if v)


def format_discovery_result(state: AppState, result: Dict[str, Any]) -> str:
    modules = result.get("modules") or []
    if not modules:
        return gui_t(state, "uds_discover_none")
    lines: List[str] = header_lines(gui_t(state, "uds_discover"))
    proto = result.get("protocol") or "?"
    addressing = result.get("addressing") or "?"
    lines.append(f"  {gui_t(state, 'uds_discover_found')}: {len(modules)}")
    lines.append(f"  {gui_t(state, 'uds_discover_protocol')}: {proto} ({addressing})")
    vin = result.get("vin")
    if vin:
        lines.append(f"  {gui_t(state, 'uds_discover_vin')}: {vin}")

    for mod in modules:
        tx = getattr(mod, "tx_id", None)
        rx = getattr(mod, "rx_id", None)
        lines.append(f"\n  - TX {tx} -> RX {rx}")
        responses = getattr(mod, "responses", None)
        if responses:
            lines.append(f"    {gui_t(state, 'uds_discover_responses')}: {_safe_join(responses)}")
        alt = getattr(mod, "alt_tx_ids", None)
        if alt:
            lines.append(f"    {gui_t(state, 'uds_discover_alt_tx')}: {_safe_join(alt)}")
        fp = getattr(mod, "fingerprint", None) or {}
        if fp.get("vin"):
            lines.append(f"    VIN: {fp.get('vin')}")
        if getattr(mod, "module_type", None):
            lines.append(f"    {gui_t(state, 'uds_discover_type')}: {getattr(mod, 'module_type')}")
        summary = fp.get("dtc_summary") or {}
        if summary:
            counts = " ".join(f"{k}:{v}" for k, v in summary.items())
            lines.append(f"    {gui_t(state, 'uds_discover_dtcs_summary')}: {counts}")
        if getattr(mod, "requires_security", False):
            lines.append(f"    {gui_t(state, 'uds_discover_security')}")
        confidence = getattr(mod, "confidence", None)
        if confidence is not None:
            lines.append(f"    {gui_t(state, 'uds_discover_confidence')}: {confidence}")
    return "\n".join(lines)
