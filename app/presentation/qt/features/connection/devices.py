from __future__ import annotations

from typing import List, Optional, Tuple

DeviceEntry = Tuple[str, str, Optional[int]]


_OBD_NAME_TOKENS = (
    "veepeak",
    "obd",
    "obdlink",
    "vlinker",
    "elm",
    "car scanner",
    "scan tool",
    "scantool",
    "diagnostic",
    "vgate",
)

_NON_ADAPTER_TOKENS = (
    "airpods",
    "iphone",
    "watch",
    "macbook",
    "ipad",
    "beats",
    "bose",
    "sony",
    "jabra",
)


def looks_like_obd_adapter(name: str) -> bool:
    n = (name or "").lower()
    return any(token in n for token in _OBD_NAME_TOKENS)


def format_port_short(port: str) -> str:
    p = str(port)
    if p.startswith("ble:"):
        addr = p.split(":", 1)[1]
        return f"BLE \u2022 \u2026{addr[-5:]}" if len(addr) > 6 else f"BLE \u2022 {addr}"
    if p.startswith("/dev/"):
        return f"USB \u2022 {p.split('/')[-1]}"
    return p


def _rssi_str(rssi: Optional[int]) -> Optional[str]:
    if isinstance(rssi, int) and rssi > -999:
        return f"{rssi} dBm"
    return None


def format_device_label(port: str, name: str, rssi: Optional[int]) -> str:
    port_s = str(port)
    name_s = (str(name) or "").strip() or "-"
    rssi_s = _rssi_str(rssi)

    if port_s.startswith("ble:"):
        # Keep the list clean: show address only when the name is missing.
        parts = [name_s]
        if name_s == "-":
            addr = port_s.split(":", 1)[1]
            short = f"\u2026{addr[-5:]}" if len(addr) > 6 else addr
            parts.append(f"BLE {short}")
        else:
            parts.append("BLE")
        if rssi_s:
            parts.append(rssi_s)
        return " \u2022 ".join(parts)

    if port_s.startswith("/dev/"):
        dev = port_s.split("/")[-1]
        return f"{dev} \u2022 USB serial"

    parts = [name_s, port_s]
    if rssi_s:
        parts.append(rssi_s)
    return " \u2022 ".join(parts)


def format_selected_summary(port: str, device_list: List[DeviceEntry]) -> str:
    for p, name, rssi in device_list:
        if p != port:
            continue
        name_s = (str(name) or "").strip() or "-"
        rssi_s = _rssi_str(rssi)
        parts = [name_s, format_port_short(port)]
        if rssi_s:
            parts.append(rssi_s)
        return " \u2022 ".join(parts)
    return format_port_short(port)


def score_device(port: str, name: str, rssi: Optional[int]) -> int:
    n = (name or "").strip()
    score = 0
    if looks_like_obd_adapter(n):
        score += 1000
    nn = n.lower()
    if any(token in nn for token in _NON_ADAPTER_TOKENS):
        score -= 800
    if isinstance(rssi, int) and rssi > -999:
        # RSSI is negative; closer to 0 is better. Map [-100..0] -> [0..100].
        score += max(0, min(100, 100 + rssi))
    if str(port).startswith("ble:"):
        score += 10
    return score


def sort_devices(devices: List[DeviceEntry]) -> List[DeviceEntry]:
    return sorted(devices, key=lambda d: score_device(d[0], d[1], d[2]), reverse=True)


def preferred_row(devices: List[DeviceEntry], *, show_all: bool) -> Optional[int]:
    if not devices:
        return None
    if not show_all:
        # In filtered mode we *usually* only show adapters, but our BLE heuristics may
        # still surface a few "candidates". Avoid auto-selecting a random device when
        # there are multiple options.
        for idx, (_, name, _) in enumerate(devices):
            if looks_like_obd_adapter(name):
                return idx
        if len(devices) == 1:
            return 0
        return None
    for idx, (_, name, _) in enumerate(devices):
        if looks_like_obd_adapter(name):
            return idx
    return None
