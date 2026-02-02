from __future__ import annotations

import asyncio
import threading
from typing import Optional, Tuple

from .config import ble_scan_timeout_s, ble_service_uuid, ble_rx_uuid, ble_tx_uuid


class BleSerial:
    def __init__(self, address: str, *, timeout: float = 3.0):
        self.address = address
        self.timeout = timeout
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._client = None
        self._rx_uuid: Optional[str] = ble_rx_uuid()
        self._tx_uuid: Optional[str] = ble_tx_uuid()
        self._service_uuid: Optional[str] = ble_service_uuid()
        self._buffer = bytearray()
        self._lock = threading.Lock()
        self._is_open = False

    @property
    def is_open(self) -> bool:
        return self._is_open

    @property
    def in_waiting(self) -> int:
        with self._lock:
            return len(self._buffer)

    def open(self) -> None:
        if self._is_open:
            return
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        fut = asyncio.run_coroutine_threadsafe(self._connect(), self._loop)
        fut.result(timeout=self.timeout + 5)
        self._is_open = True

    def close(self) -> None:
        self._is_open = False
        if self._loop and self._client:
            try:
                fut = asyncio.run_coroutine_threadsafe(self._disconnect(), self._loop)
                fut.result(timeout=self.timeout + 2)
            except Exception:
                pass
        if self._loop:
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=1.0)
        self._thread = None
        self._loop = None
        self._client = None

    def reset_input_buffer(self) -> None:
        with self._lock:
            self._buffer.clear()

    def reset_output_buffer(self) -> None:
        return None

    def flush(self) -> None:
        return None

    def read(self, size: int = 1) -> bytes:
        if size <= 0:
            return b""
        with self._lock:
            if not self._buffer:
                return b""
            data = self._buffer[:size]
            del self._buffer[:size]
            return bytes(data)

    def write(self, data: bytes) -> int:
        if not self._is_open or not data:
            return 0
        if not self._rx_uuid:
            raise RuntimeError("BLE RX characteristic not set")
        fut = asyncio.run_coroutine_threadsafe(
            self._client.write_gatt_char(self._rx_uuid, data, response=False),
            self._loop,
        )
        fut.result(timeout=self.timeout)
        return len(data)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _connect(self) -> None:
        from bleak import BleakClient, BleakScanner

        device = None
        scan_timeout = max(self.timeout, ble_scan_timeout_s())
        try:
            if hasattr(BleakScanner, "find_device_by_address"):
                device = await BleakScanner.find_device_by_address(
                    self.address,
                    timeout=scan_timeout,
                )
            else:
                devices = await BleakScanner.discover(timeout=scan_timeout)
                for dev in devices or []:
                    if getattr(dev, "address", None) == self.address:
                        device = dev
                        break
        except Exception:
            device = None
        if device is None:
            raise RuntimeError(
                "BLE device not found. If it's connected in macOS Bluetooth settings, "
                "disconnect it and try again."
            )

        self._client = BleakClient(device)
        await self._client.connect(timeout=self.timeout)
        await self._select_characteristics()
        if not self._tx_uuid:
            raise RuntimeError("BLE TX characteristic not set")
        await self._client.start_notify(self._tx_uuid, self._on_notify)

    async def _disconnect(self) -> None:
        try:
            if self._tx_uuid:
                await self._client.stop_notify(self._tx_uuid)
        except Exception:
            pass
        try:
            await self._client.disconnect()
        except Exception:
            pass

    async def _select_characteristics(self) -> None:
        if self._rx_uuid and self._tx_uuid:
            return
        if hasattr(self._client, "get_services"):
            services = await self._client.get_services()
        else:
            services = getattr(self._client, "services", None)
            if services is None:
                raise RuntimeError(
                    "BLE services not available; please update the bleak package."
                )
        # Known BLE UART profiles (service, rx, tx) in priority order.
        known_profiles = [
            (
                "0000fff0-0000-1000-8000-00805f9b34fb",
                "0000fff2-0000-1000-8000-00805f9b34fb",
                "0000fff1-0000-1000-8000-00805f9b34fb",
            ),
            (
                "49535343-fe7d-4ae5-8fa9-9fafd205e455",
                "49535343-6daa-4d02-abf6-19569aca69fe",
                "49535343-aca3-481c-91ec-d85e28a60318",
            ),
            (
                "6e400001-b5a3-f393-e0a9-e50e24dcca9e",
                "6e400002-b5a3-f393-e0a9-e50e24dcca9e",
                "6e400003-b5a3-f393-e0a9-e50e24dcca9e",
            ),
            (
                "0000ffe0-0000-1000-8000-00805f9b34fb",
                "0000ffe1-0000-1000-8000-00805f9b34fb",
                "0000ffe1-0000-1000-8000-00805f9b34fb",
            ),
        ]
        service_filter = (self._service_uuid or "").lower()
        rx_uuid, tx_uuid = None, None
        service_map = {service.uuid.lower(): service for service in services}
        for svc_uuid, rx_known, tx_known in known_profiles:
            if service_filter and svc_uuid != service_filter:
                continue
            service = service_map.get(svc_uuid)
            if not service:
                continue
            char_uuids = {ch.uuid.lower() for ch in service.characteristics}
            if rx_known in char_uuids and tx_known in char_uuids:
                self._rx_uuid = self._rx_uuid or rx_known
                self._tx_uuid = self._tx_uuid or tx_known
                return

        for service in services:
            if service_filter and service.uuid.lower() != service_filter:
                continue
            write_chars = []
            notify_chars = []
            for ch in service.characteristics:
                props = {p.lower() for p in ch.properties}
                if "write" in props or "write-without-response" in props:
                    write_chars.append(ch.uuid)
                if "notify" in props or "indicate" in props:
                    notify_chars.append(ch.uuid)
            if write_chars and notify_chars:
                rx_uuid = write_chars[0]
                tx_uuid = notify_chars[0]
                break
        if not rx_uuid or not tx_uuid:
            # Fallback: pick any write/notify across services
            for service in services:
                write_chars = []
                notify_chars = []
                for ch in service.characteristics:
                    props = {p.lower() for p in ch.properties}
                    if "write" in props or "write-without-response" in props:
                        write_chars.append(ch.uuid)
                    if "notify" in props or "indicate" in props:
                        notify_chars.append(ch.uuid)
                if write_chars and notify_chars:
                    rx_uuid = write_chars[0]
                    tx_uuid = notify_chars[0]
                    break
        self._rx_uuid = self._rx_uuid or rx_uuid
        self._tx_uuid = self._tx_uuid or tx_uuid

    def _on_notify(self, _: int, data: bytearray) -> None:
        if not data:
            return
        with self._lock:
            self._buffer.extend(data)
