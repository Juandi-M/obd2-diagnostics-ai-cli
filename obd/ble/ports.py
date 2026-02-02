from __future__ import annotations

import asyncio
import threading
from typing import List, Optional, Tuple

from .config import ble_address, ble_name, ble_scan_timeout_s


_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None
_loop_ready = threading.Event()
_loop_lock = threading.Lock()


def _loop_worker(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    _loop_ready.set()
    loop.run_forever()


def _ensure_loop() -> asyncio.AbstractEventLoop:
    global _loop, _loop_thread
    with _loop_lock:
        if _loop and _loop_thread and _loop_thread.is_alive():
            return _loop
        _loop_ready.clear()
        _loop = asyncio.new_event_loop()
        _loop_thread = threading.Thread(
            target=_loop_worker,
            args=(_loop,),
            name="ble-scan-loop",
            daemon=True,
        )
        _loop_thread.start()
    _loop_ready.wait(timeout=1.0)
    return _loop


def _run(coro):
    loop = _ensure_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()


def find_ble_ports() -> List[str]:
    address = ble_address()
    if address:
        return [f"ble:{address}"]

    try:
        from bleak import BleakScanner
    except Exception:
        return []

    target_name = ble_name()

    def _device_name(dev, adv) -> str:
        return (
            (getattr(dev, "name", None) or "").strip()
            or (getattr(dev, "local_name", None) or "").strip()
            or (getattr(adv, "local_name", None) or "").strip()
        )

    async def _scan() -> List[str]:
        try:
            try:
                result = await BleakScanner.discover(
                    timeout=ble_scan_timeout_s(),
                    return_adv=True,
                )
            except TypeError:
                result = await BleakScanner.discover(timeout=ble_scan_timeout_s())
        except Exception:
            return []

        items = []
        if isinstance(result, dict):
            items = list(result.values())
        elif isinstance(result, list):
            items = result
        else:
            items = [result]

        named_matches: List[Tuple[int, str]] = []
        unnamed: List[Tuple[int, str]] = []
        others: List[Tuple[int, str]] = []
        seen = set()

        def _rssi(dev, adv) -> int:
            rssi = getattr(dev, "rssi", None)
            if rssi is None and adv is not None:
                rssi = getattr(adv, "rssi", None)
            if rssi is None:
                return -999
            try:
                return int(rssi)
            except Exception:
                return -999

        def _service_uuids(adv) -> List[str]:
            if adv is None:
                return []
            uuids = getattr(adv, "service_uuids", None) or []
            return [str(u).lower() for u in uuids]

        known_service_tokens = {
            "6e400001-b5a3-f393-e0a9-e50e24dcca9e",  # Nordic UART
            "0000ffe0-0000-1000-8000-00805f9b34fb",  # HM-10
            "0000fff0-0000-1000-8000-00805f9b34fb",
        }
        for item in items:
            if isinstance(item, tuple) and len(item) == 2:
                dev, adv = item
            else:
                dev, adv = item, None
            name = _device_name(dev, adv)
            addr = f"ble:{dev.address}"
            if addr in seen:
                continue
            seen.add(addr)
            rssi = _rssi(dev, adv)
            svc_uuids = _service_uuids(adv)
            has_known_service = any(u in known_service_tokens for u in svc_uuids)
            if target_name:
                if target_name.lower() in name.lower():
                    named_matches.append((rssi, addr))
                continue
            if name:
                if any(token in name.lower() for token in ["veepeak", "obdcheck", "obd"]):
                    named_matches.append((rssi, addr))
                else:
                    others.append((rssi, addr))
            else:
                if has_known_service:
                    named_matches.append((rssi, addr))
                else:
                    unnamed.append((rssi, addr))

        if named_matches:
            return [addr for _, addr in sorted(named_matches, key=lambda x: x[0], reverse=True)]
        # If we can't identify an OBD/BLE adapter by name or service, don't try random devices.
        return []

    try:
        return _run(_scan())
    except Exception:
        return []


def scan_ble_devices(include_all: bool = False) -> Tuple[List[Tuple[str, str]], Optional[str]]:
    try:
        from bleak import BleakScanner
    except Exception:
        return [], "ble_unavailable"

    def _device_name(dev, adv) -> str:
        return (
            (getattr(dev, "name", None) or "").strip()
            or (getattr(dev, "local_name", None) or "").strip()
            or (getattr(adv, "local_name", None) or "").strip()
        )

    def _rssi(dev, adv) -> int:
        rssi = getattr(dev, "rssi", None)
        if rssi is None and adv is not None:
            rssi = getattr(adv, "rssi", None)
        if rssi is None:
            return -999
        try:
            return int(rssi)
        except Exception:
            return -999

    def _service_uuids(adv) -> List[str]:
        if adv is None:
            return []
        uuids = getattr(adv, "service_uuids", None) or []
        return [str(u).lower() for u in uuids]

    known_service_tokens = {
        "6e400001-b5a3-f393-e0a9-e50e24dcca9e",
        "0000ffe0-0000-1000-8000-00805f9b34fb",
        "0000fff0-0000-1000-8000-00805f9b34fb",
    }

    async def _scan() -> List[Tuple[str, str]]:
        try:
            try:
                result = await BleakScanner.discover(
                    timeout=ble_scan_timeout_s(),
                    return_adv=True,
                )
            except TypeError:
                result = await BleakScanner.discover(timeout=ble_scan_timeout_s())
        except Exception:
            return [], "ble_error"

        items = []
        if isinstance(result, dict):
            items = list(result.values())
        elif isinstance(result, list):
            items = result
        else:
            items = [result]

        devices: List[Tuple[int, str, str]] = []
        seen = set()
        for item in items:
            if isinstance(item, tuple) and len(item) == 2:
                dev, adv = item
            else:
                dev, adv = item, None
            addr = f"ble:{dev.address}"
            if addr in seen:
                continue
            seen.add(addr)
            name = _device_name(dev, adv) or "-"
            rssi = _rssi(dev, adv)

            if include_all:
                devices.append((rssi, addr, name))
                continue

            svc_uuids = _service_uuids(adv)
            has_known_service = any(u in known_service_tokens for u in svc_uuids)
            name_hit = any(token in name.lower() for token in ["veepeak", "obdcheck", "obd"])
            if name_hit or has_known_service:
                devices.append((rssi, addr, name))

        devices.sort(key=lambda x: x[0], reverse=True)
        return [(addr, name) for _, addr, name in devices], None

    try:
        return _run(_scan())
    except Exception:
        return [], "ble_error"
