from __future__ import annotations

from typing import List

from app.application.state import AppState
from app.application.time_utils import cr_timestamp
from app.domain.entities import NotConnectedError
from app.presentation.qt.app_vm import get_vm
from app.presentation.qt.utils.text import header_lines, subheader_lines


def full_scan(state: AppState) -> str:
    if not state.active_scanner():
        raise NotConnectedError("Not connected")

    lines: List[str] = []
    lines.extend(header_lines("FULL DIAGNOSTIC SCAN"))
    lines.append("")
    lines.append(f"  Report time: {cr_timestamp()}")
    lines.append("")

    info = get_vm().scan_vm.get_vehicle_info()
    lines.extend(subheader_lines("Vehicle connection"))
    lines.append(f"  ELM Version: {info.get('elm_version', 'unknown')}")
    lines.append(f"  Protocol: {info.get('protocol', 'unknown')}")
    lines.append(f"  MIL Status: {info.get('mil_on', 'unknown')}")
    lines.append(f"  DTC Count: {info.get('dtc_count', 'unknown')}")
    lines.append("")

    lines.extend(subheader_lines("TROUBLE CODES"))
    dtcs = get_vm().scan_vm.read_dtcs()
    if dtcs:
        for dtc in dtcs:
            status = f" ({dtc.status})" if dtc.status != "stored" else ""
            lines.append(f"  {dtc.code}{status}: {dtc.description}")
    else:
        lines.append("  No trouble codes found.")
    lines.append("")

    lines.extend(subheader_lines("READINESS MONITORS"))
    readiness = get_vm().scan_vm.read_readiness()
    if readiness:
        for name, status in readiness.items():
            lines.append(f"  {name}: {status.status_str}")
    else:
        lines.append("  Readiness data unavailable.")
    lines.append("")

    lines.extend(subheader_lines("LIVE DATA"))
    readings = get_vm().scan_vm.read_live_data()
    if readings:
        for reading in readings.values():
            lines.append(f"  {reading.name}: {reading.value} {reading.unit}")
    else:
        lines.append("  Live data not available.")

    lines.append("")
    lines.append("=" * 60)
    lines.append(f"  Report time: {cr_timestamp()}")
    lines.append("=" * 60)
    return "\n".join(lines)


def read_codes(state: AppState) -> str:
    if not state.active_scanner():
        raise NotConnectedError("Not connected")
    dtcs = get_vm().scan_vm.read_dtcs()
    lines: List[str] = []
    lines.extend(header_lines("TROUBLE CODES"))
    lines.append(f"  Time: {cr_timestamp()}")
    lines.append("")
    if dtcs:
        for dtc in dtcs:
            status = f" [{dtc.status}]" if dtc.status != "stored" else ""
            lines.append(f"  {dtc.code}{status}: {dtc.description}")
    else:
        lines.append("  No trouble codes found.")
    return "\n".join(lines)


def readiness(state: AppState) -> str:
    if not state.active_scanner():
        raise NotConnectedError("Not connected")
    readiness_payload = get_vm().scan_vm.read_readiness()
    lines: List[str] = []
    lines.extend(header_lines("READINESS MONITORS"))
    lines.append(f"  Time: {cr_timestamp()}")
    lines.append("")
    if not readiness_payload:
        lines.append("  Readiness data unavailable.")
        return "\n".join(lines)
    for name, status in readiness_payload.items():
        lines.append(f"  {name}: {status.status_str}")
    return "\n".join(lines)


def freeze_frame(state: AppState) -> str:
    if not state.active_scanner():
        raise NotConnectedError("Not connected")
    freeze = get_vm().scan_vm.read_freeze_frame()
    lines: List[str] = []
    lines.extend(header_lines("FREEZE FRAME DATA"))
    lines.append(f"  Time: {cr_timestamp()}")
    lines.append("")
    if freeze:
        lines.append(f"  DTC: {freeze.dtc_code}")
        for reading in freeze.readings.values():
            lines.append(f"  {reading.name}: {reading.value} {reading.unit}")
    else:
        lines.append("  No freeze frame data available.")
        lines.append("  (Freeze frames are captured when a DTC is stored)")
    return "\n".join(lines)


def clear_codes(state: AppState) -> str:
    if not state.active_scanner():
        raise NotConnectedError("Not connected")
    lines: List[str] = []
    lines.extend(header_lines("CLEAR CODES"))
    lines.append(f"  Time: {cr_timestamp()}")
    lines.append("")
    ok = get_vm().scan_vm.clear_codes()
    lines.append("  Codes cleared successfully." if ok else "  Failed to clear codes.")
    return "\n".join(lines)

