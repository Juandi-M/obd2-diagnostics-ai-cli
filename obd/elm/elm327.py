from __future__ import annotations

import re
import time
from typing import Optional, List, Callable

import serial

from .errors import CommunicationError, DeviceDisconnectedError
from .ports import find_ports
from .init import initialize_elm
from .protocol import negotiate_protocol as _negotiate_protocol, get_protocol as _get_protocol


class ELM327:
    BAUD_RATES = [38400, 9600, 115200, 57600, 19200]

    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = 38400,
        timeout: float = 3.0,
        raw_logger: Optional[Callable[[str, str, List[str]], None]] = None,
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection: Optional[serial.Serial] = None
        self.protocol: Optional[str] = None
        self.elm_version: Optional[str] = None
        self._is_connected = False

        self.raw_logger = raw_logger
        self.last_command: Optional[str] = None
        self.last_lines: List[str] = []
        self.last_error: Optional[str] = None
        self.last_duration_s: Optional[float] = None
        self.last_raw_text: Optional[str] = None

        # Default headers ON for robust multi-ECU parsing
        self.headers_on = True

    @property
    def is_connected(self) -> bool:
        if not self._is_connected:
            return False
        if not self.connection:
            return False
        try:
            return self.connection.is_open
        except Exception:
            return False

    @staticmethod
    def find_ports(include_bluetooth: bool = False) -> List[str]:
        return find_ports(include_bluetooth=include_bluetooth)

    @staticmethod
    def find_bluetooth_ports() -> List[str]:
        from obd.bluetooth.ports import find_bluetooth_ports

        return find_bluetooth_ports()

    def connect(self) -> bool:
        if not self.port:
            ports = self.find_ports()
            if not ports:
                raise ConnectionError("No ELM327 adapter found. Check USB connection.")
            self.port = ports[0]

        try:
            self.connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
            )
            time.sleep(0.2)

            if not initialize_elm(self):
                self._is_connected = False
                raise ConnectionError("ELM327 initialization failed")

            self._is_connected = True
            return True

        except serial.SerialException as e:
            self._is_connected = False
            raise ConnectionError(f"Serial port error: {e}")

    def _check_connection(self) -> None:
        if not self.connection:
            self._is_connected = False
            raise DeviceDisconnectedError("Not connected to ELM327")
        try:
            if not self.connection.is_open:
                self._is_connected = False
                raise DeviceDisconnectedError("Serial port is closed")
        except (OSError, serial.SerialException) as e:
            self._is_connected = False
            raise DeviceDisconnectedError(f"Device disconnected: {e}")

    def send_raw_lines(
        self,
        command: str,
        timeout: Optional[float] = None,
        silence_timeout: float = 0.25,
        min_wait_before_silence_break: float = 0.75,
    ) -> List[str]:
        """
        Robust read:
        - Primary termination: '>' prompt
        - Secondary: silence break AFTER min_wait_before_silence_break
        """
        self._check_connection()
        if timeout is None:
            timeout = self.timeout

        try:
            self.last_command = command
            self.last_error = None
            self.last_duration_s = None
            self.last_raw_text = None
            try:
                self.connection.reset_input_buffer()
                self.connection.reset_output_buffer()
            except Exception:
                pass

            if self.raw_logger:
                self.raw_logger("TX", command, [])

            self.connection.write(f"{command}\r".encode("ascii", errors="ignore"))
            self.connection.flush()

            buf = bytearray()
            start = time.monotonic()
            last_rx = start
            received_any = False
            received_meaningful = False
            prompt_seen = False

            def _is_meaningful(lines: List[str]) -> bool:
                for ln in lines:
                    up = ln.strip().upper()
                    if not up:
                        continue
                    if up.startswith("SEARCHING"):
                        continue
                    if up.startswith("BUS INIT") and "ERROR" not in up:
                        continue
                    return True
                return False

            while True:
                now = time.monotonic()
                if (now - start) > timeout:
                    break

                n = self.connection.in_waiting
                if n:
                    chunk = self.connection.read(n)
                    buf.extend(chunk)
                    last_rx = now
                    received_any = True
                    if b">" in chunk or b">" in buf:
                        prompt_seen = True
                    if not received_meaningful:
                        text = buf.decode("utf-8", errors="ignore")
                        lines = [
                            ln.strip()
                            for ln in text.replace(">", "").replace("\r", "\n").split("\n")
                            if ln.strip()
                        ]
                        if _is_meaningful(lines):
                            received_meaningful = True
                    if prompt_seen and received_meaningful:
                        break
                else:
                    if prompt_seen and received_meaningful:
                        break
                    if (
                        received_any
                        and received_meaningful
                        and (now - start) >= min_wait_before_silence_break
                        and (now - last_rx) > silence_timeout
                    ):
                        break
                    time.sleep(0.01)

            text = buf.decode("utf-8", errors="ignore")
            text = text.replace(">", "").replace("\r", "\n")
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
            self.last_lines = lines
            self.last_raw_text = text
            self.last_duration_s = time.monotonic() - start

            if self.raw_logger:
                self.raw_logger("RX", command, lines)

            return lines

        except (OSError, serial.SerialException) as e:
            self._is_connected = False
            self.last_error = str(e)
            self.last_duration_s = time.monotonic() - start
            error_str = str(e).lower()
            if "device not configured" in error_str or "disconnected" in error_str:
                raise DeviceDisconnectedError(f"Device disconnected: {e}")
            raise CommunicationError(f"Communication error: {e}")
        except Exception as e:
            self.last_error = str(e)
            self.last_duration_s = time.monotonic() - start
            raise CommunicationError(f"Unexpected error: {e}")

    def send_raw(self, command: str, timeout: Optional[float] = None) -> str:
        return " ".join(self.send_raw_lines(command, timeout=timeout))

    def send_obd(self, command: str) -> str:
        try:
            resp_lines = self.send_raw_lines(command, timeout=max(self.timeout, 2.0))
        except DeviceDisconnectedError:
            return "DISCONNECTED"
        except CommunicationError:
            return "ERROR"

        up_joined = " ".join(resp_lines).upper()

        if "NO DATA" in up_joined:
            return "NO DATA"
        if "UNABLE TO CONNECT" in up_joined:
            return "NO CONNECT"
        if "ERROR" in up_joined:
            return "ERROR"
        if "?" in up_joined:
            return "INVALID"

        return "".join(ch for ch in up_joined if ch in "0123456789ABCDEF")

    def send_obd_lines(self, command: str) -> List[str]:
        return self.send_raw_lines(command, timeout=max(self.timeout, 2.0))

    def test_vehicle_connection(
        self,
        retries: int = 2,
        retry_delay_s: float = 0.8,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        Try multiple times because some ECUs respond only after the first "SEARCHING...".
        """
        use_timeout = max(self.timeout, 2.0) if timeout is None else timeout
        for attempt in range(retries + 1):
            lines = self.send_raw_lines("0100", timeout=use_timeout)
            joined = " ".join(lines).upper()
            compact = joined.replace(" ", "")

            if "4100" in compact:
                if self.headers_on:
                    looks_like_header = any(
                        re.match(r"^[0-9A-F]{3,8}\s", ln.strip().upper()) for ln in lines
                    )
                    if not looks_like_header:
                        self.headers_on = False
                        try:
                            self.send_raw_lines("ATH0", timeout=1.0)
                            self.send_raw_lines("ATS0", timeout=1.0)
                        except Exception:
                            pass
                return True

            if "SEARCHING" in joined or "BUS INIT" in joined:
                if attempt < retries:
                    time.sleep(retry_delay_s)
                    continue
                return False

            if any(err in joined for err in ["NO DATA", "UNABLE TO CONNECT", "CAN ERROR", "STOPPED"]):
                if attempt < retries:
                    time.sleep(retry_delay_s)
                    continue
                return False

            if not joined:
                if attempt < retries:
                    time.sleep(retry_delay_s)
                    continue
                return False

            if attempt < retries:
                time.sleep(retry_delay_s)
                continue
            return False

        return False

    def negotiate_protocol(
        self,
        timeout_s: Optional[float] = None,
        retries: int = 1,
        retry_delay_s: float = 0.5,
    ) -> str:
        return _negotiate_protocol(
            self,
            timeout_s=timeout_s,
            retries=retries,
            retry_delay_s=retry_delay_s,
        )

    def get_protocol(self) -> str:
        return _get_protocol(self)

    def close(self):
        self._is_connected = False
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            finally:
                self.connection = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
