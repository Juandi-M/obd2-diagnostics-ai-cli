from __future__ import annotations

import time
from typing import Optional, List, Tuple, Callable

from ..elm import ELM327
from ..elm import DeviceDisconnectedError, CommunicationError

from ..protocol import (
    group_by_ecu,
    merge_payloads,
    find_obd_response_payload,
)


class ScannerError(Exception):
    pass


class NotConnectedError(ScannerError):
    pass


class ConnectionLostError(ScannerError):
    pass


class BaseScanner:
    """
    Base for OBDScanner:
    - connection lifecycle
    - retry wrapper
    - robust query helper (_obd_query_payload)
    """

    ERROR_RESPONSES = {"NO DATA", "ERROR", "NO CONNECT", "INVALID", "DISCONNECTED"}

    ECU_PREFER = [
        "7E8", "7E0", "7E9", "7E1", "7EA", "7E2", "7EB", "7E3",
        "7EC", "7E4", "7ED", "7E5", "7EE", "7E6", "7EF", "7E7"
    ]

    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = 38400,
        raw_logger: Optional[Callable[[str, str, List[str]], None]] = None,
    ):
        self.elm = ELM327(port=port, baudrate=baudrate, raw_logger=raw_logger)
        self._connected = False

    # -----------------------------
    # Connection
    # -----------------------------
    def connect(self) -> bool:
        self.elm.connect()
        connect_timeout = max(self.elm.timeout, 8.0)

        # First: give auto protocol enough time to respond
        if self.elm.test_vehicle_connection(retries=3, retry_delay_s=1.0, timeout=connect_timeout):
            self._connected = True
            return True

        # If auto failed, try to lock into a working protocol (safe to fail)
        try:
            self.elm.negotiate_protocol(timeout_s=connect_timeout, retries=1, retry_delay_s=0.6)
        except Exception:
            pass

        if not self.elm.test_vehicle_connection(retries=2, retry_delay_s=1.0, timeout=connect_timeout):
            self._connected = False
            raise ConnectionError("No response from vehicle ECU")

        self._connected = True
        return True

    def auto_connect(self) -> str:
        ports = ELM327.find_ports()
        if not ports:
            raise ConnectionError("No USB serial ports found. Is the ELM327 plugged in?")

        last_error: Optional[Exception] = None

        for port in ports:
            try:
                self.elm.port = port
                self.connect()
                return port
            except Exception as e:
                last_error = e
                try:
                    self.disconnect()
                except Exception:
                    pass

        raise ConnectionError(f"No responding OBD device found. Tried: {ports}. Last error: {last_error}")

    def disconnect(self):
        self._connected = False
        try:
            self.elm.close()
        except Exception:
            pass

    @property
    def is_connected(self) -> bool:
        if not self._connected:
            return False
        if not self.elm.is_connected:
            self._connected = False
            return False
        return True

    def _check_connected(self) -> None:
        if not self.is_connected:
            raise NotConnectedError("Not connected to vehicle")

    def _handle_disconnection(self) -> None:
        self._connected = False

    # -----------------------------
    # Stage 1 retry wrapper
    # -----------------------------
    def _send_obd_lines_retry(self, command: str, retries: int = 1) -> List[str]:
        last_lines: List[str] = []
        for attempt in range(retries + 1):
            try:
                lines = self.elm.send_obd_lines(command)
                last_lines = lines
                joined = " ".join(lines).upper()

                if not any(err in joined for err in ["NO DATA", "UNABLE TO CONNECT", "ERROR", "STOPPED", "BUS", "CAN ERROR", "?", "BUFFER FULL"]):
                    return lines

            except DeviceDisconnectedError:
                self._handle_disconnection()
                raise ConnectionLostError("Device disconnected")

            if attempt < retries:
                time.sleep(0.15)

        return last_lines

    # -----------------------------
    # Stage 1 robust helper
    # -----------------------------
    def _obd_query_payload(self, command: str, expected_prefix: List[str]) -> Optional[Tuple[str, List[str]]]:
        self._check_connected()
        try:
            lines = self._send_obd_lines_retry(command, retries=1)
        except DeviceDisconnectedError:
            self._handle_disconnection()
            raise ConnectionLostError("Device disconnected")
        except CommunicationError as e:
            raise ScannerError(f"Communication error: {e}")

        grouped = group_by_ecu(lines, headers_on=self.elm.headers_on)
        merged = merge_payloads(grouped, headers_on=self.elm.headers_on)

        prefer = self.ECU_PREFER if self.elm.headers_on else None
        return find_obd_response_payload(merged, expected_prefix, prefer_ecus=prefer)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
