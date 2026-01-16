from __future__ import annotations

import re
import time
from typing import Optional, List, Callable

import serial
import serial.tools.list_ports


class CommunicationError(Exception):
    pass


class DeviceDisconnectedError(CommunicationError):
    pass


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

        # Optional logger: fn(direction, command, lines)
        self.raw_logger = raw_logger

        # Nivel 1: default headers ON for robust multi-ECU parsing
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
    def find_ports() -> List[str]:
        ranked: List[tuple[int, str]] = []
        try:
            ports_list = serial.tools.list_ports.comports()
        except Exception:
            return []

        for p in ports_list:
            dev = (p.device or "").lower()
            desc = (p.description or "").lower()

            if "bluetooth" in dev or "debug-console" in dev:
                continue

            score = 0
            if "usb" in desc:
                score += 2
            if any(x in desc for x in ["elm", "ch340", "pl2303", "ftdi", "cp210"]):
                score += 3
            if "usbserial" in dev or "wchusbserial" in dev:
                score += 2
            if "slab_usbtouart" in dev or "silicon labs" in desc:
                score += 2

            if score > 0 and p.device:
                ranked.append((score, p.device))

        ranked.sort(reverse=True)
        return [dev for _, dev in ranked]

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

            if not self._initialize():
                self._is_connected = False
                raise ConnectionError("ELM327 initialization failed")

            self._is_connected = True
            return True

        except serial.SerialException as e:
            self._is_connected = False
            raise ConnectionError(f"Serial port error: {e}")

    def _initialize(self) -> bool:
        try:
            resp_lines = self.send_raw_lines("ATZ", timeout=2.0)
            resp = "\n".join(resp_lines)
            self.elm_version = self._extract_version(resp) or "unknown"

            # Basic config
            self.send_raw_lines("ATE0", timeout=1.0)  # echo off
            self.send_raw_lines("ATL0", timeout=1.0)  # linefeeds off
            self.send_raw_lines("ATS0", timeout=1.0)  # spaces off

            # Headers ON for multi-ECU robustness (you can toggle later)
            if self.headers_on:
                self.send_raw_lines("ATH1", timeout=1.0)
            else:
                self.send_raw_lines("ATH0", timeout=1.0)

            self.send_raw_lines("ATAT1", timeout=1.0)  # adaptive timing
            self.send_raw_lines("ATSP0", timeout=1.0)  # auto protocol

            # Allow long messages if supported (safe ignore)
            try:
                self.send_raw_lines("ATAL", timeout=1.0)
            except CommunicationError:
                pass

            # Verify headers really work (some clones lie)
            # If headers_on=True but we can't see header-like lines on 0100, disable internally.
            if self.headers_on:
                try:
                    lines = self.send_raw_lines("0100", timeout=max(self.timeout, 2.0))
                    # heuristic: a CAN header is usually 3 hex chars like 7E8/7E0/7E9...
                    looks_like_header = any(re.match(r"^[0-9A-F]{3,8}\s", ln.strip().upper()) for ln in lines)

                    if not looks_like_header:
                        # Fall back: treat as headers_off to avoid mis-parsing
                        self.headers_on = False
                except Exception:
                    # don't fail init just for this
                    pass

            return True
        except (CommunicationError, serial.SerialException):
            return False

    @staticmethod
    def _extract_version(response: str) -> Optional[str]:
        s = response.strip()
        if not s:
            return None
        m = re.search(r"(ELM327\s*v?\s*[\w\.]+)", s, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return s[:40].strip() if s else None

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
        Sends command and returns response as a list of non-empty lines.

        Robust:
        - Primary termination: '>' prompt
        - Secondary termination: silence break AFTER at least min_wait_before_silence_break
          (prevents cutting multi-frame / multi-ECU replies)
        """
        self._check_connection()
        if timeout is None:
            timeout = self.timeout

        try:
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

            while True:
                now = time.monotonic()
                if (now - start) > timeout:
                    break

                n = self.connection.in_waiting
                if n:
                    chunk = self.connection.read(n)
                    buf.extend(chunk)
                    last_rx = now
                    if b">" in chunk or b">" in buf:
                        break
                else:
                    # Only allow silence break after we waited enough overall
                    if (now - start) >= min_wait_before_silence_break and (now - last_rx) > silence_timeout:
                        break
                    time.sleep(0.01)

            text = buf.decode("utf-8", errors="ignore")
            text = text.replace(">", "")
            text = text.replace("\r", "\n")
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

            if self.raw_logger:
                self.raw_logger("RX", command, lines)

            return lines

        except (OSError, serial.SerialException) as e:
            self._is_connected = False
            error_str = str(e).lower()
            if "device not configured" in error_str or "disconnected" in error_str:
                raise DeviceDisconnectedError(f"Device disconnected: {e}")
            raise CommunicationError(f"Communication error: {e}")
        except Exception as e:
            raise CommunicationError(f"Unexpected error: {e}")

    def send_raw(self, command: str, timeout: Optional[float] = None) -> str:
        lines = self.send_raw_lines(command, timeout=timeout)
        return " ".join(lines)

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

        hex_only = "".join(ch for ch in up_joined if ch in "0123456789ABCDEF")
        return hex_only

    def send_obd_lines(self, command: str) -> List[str]:
        return self.send_raw_lines(command, timeout=max(self.timeout, 2.0))

    def test_vehicle_connection(self) -> bool:
        response = self.send_obd("0100")
        if response in ["DISCONNECTED", "ERROR", "NO CONNECT"]:
            return False
        return "4100" in response

    def negotiate_protocol(self) -> str:
        """
        Tries ATSP0 then common CAN protocols.
        Restores ATSP0 if it can't find a working one.
        """
        # Save current (best-effort)
        try:
            current = self.send_raw("ATDPN", timeout=1.0).strip().upper()
        except Exception:
            current = ""

        candidates = ["0", "6", "7", "8", "9"]
        try:
            for p in candidates:
                self.send_raw_lines(f"ATSP{p}", timeout=1.0)
                time.sleep(0.05)
                lines = self.send_raw_lines("0100", timeout=max(self.timeout, 2.0))
                joined = " ".join(lines).upper().replace(" ", "")
                if "4100" in joined:
                    return p
        finally:
            # If we didn't return successfully, go back to auto
            try:
                self.send_raw_lines("ATSP0", timeout=1.0)
            except Exception:
                pass

        raise CommunicationError("Protocol negotiation failed (0100 did not respond)")

    def get_protocol(self) -> str:
        try:
            resp = self.send_raw("ATDPN", timeout=1.0).strip().upper()
        except (DeviceDisconnectedError, CommunicationError):
            return "Unknown (disconnected)"

        code = None
        m = re.search(r"([0-9A-F])", resp)
        if m:
            code = m.group(1)

        protocol_map = {
            "1": "SAE J1850 PWM",
            "2": "SAE J1850 VPW",
            "3": "ISO 9141-2",
            "4": "ISO 14230-4 KWP (5 baud init)",
            "5": "ISO 14230-4 KWP (fast init)",
            "6": "ISO 15765-4 CAN (11 bit, 500 kbaud)",
            "7": "ISO 15765-4 CAN (29 bit, 500 kbaud)",
            "8": "ISO 15765-4 CAN (11 bit, 250 kbaud)",
            "9": "ISO 15765-4 CAN (29 bit, 250 kbaud)",
            "A": "SAE J1939 CAN",
        }

        if code and code in protocol_map:
            self.protocol = protocol_map[code]
            return self.protocol
        return f"Unknown: {resp}"

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
