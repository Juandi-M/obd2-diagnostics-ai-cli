#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import sys


async def list_devices() -> int:
    try:
        from bleak import BleakScanner
    except Exception as exc:
        print(f"bleak not installed: {exc}")
        return 1

    try:
        result = await BleakScanner.discover(timeout=5.0, return_adv=True)
    except TypeError:
        result = await BleakScanner.discover(timeout=5.0)

    if not result:
        print("No BLE devices found.")
        return 0
    print("BLE devices:")
    items = []
    if isinstance(result, dict):
        items = list(result.values())
    elif isinstance(result, list):
        items = result
    else:
        items = [result]

    for item in items:
        if isinstance(item, tuple) and len(item) == 2:
            dev, adv = item
        else:
            dev, adv = item, None
        name = (
            getattr(dev, "name", None)
            or getattr(dev, "local_name", None)
            or getattr(adv, "local_name", None)
            or "-"
        )
        print(f"  {dev.address} | {name}")
    return 0


async def show_services(address: str) -> int:
    try:
        from bleak import BleakClient
    except Exception as exc:
        print(f"bleak not installed: {exc}")
        return 1

    async with BleakClient(address) as client:
        if not client.is_connected:
            print("Failed to connect.")
            return 1
        if hasattr(client, "get_services"):
            services = await client.get_services()
        else:
            services = getattr(client, "services", None)
            if services is None:
                print("BLE services not available. Please update the bleak package.")
                return 1
        for service in services:
            print(f"Service {service.uuid}: {service.description}")
            for ch in service.characteristics:
                props = ",".join(ch.properties)
                print(f"  Char {ch.uuid} [{props}]")
    return 0


def _run(coro) -> int:
    try:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            # Avoid closing the loop here to prevent CoreBluetooth callbacks
            # from targeting a closed loop on macOS.
            pass
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"BLE scan failed: {exc}")
        return 1


def main() -> int:
    if len(sys.argv) == 1:
        return _run(list_devices())
    if len(sys.argv) == 2:
        return _run(show_services(sys.argv[1]))
    print("Usage:")
    print("  python3 tools/ble_scan.py            # list devices")
    print("  python3 tools/ble_scan.py <address>  # show services/characteristics")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
