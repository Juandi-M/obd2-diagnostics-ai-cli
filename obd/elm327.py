"""
ELM327 Communication Module
===========================
Handles all serial communication with ELM327 OBD2 adapters.
"""

from __future__ import annotations

import re
import time
from typing import Optional, List

import serial
import serial.tools.list_ports


class ELM327:
    """
    Low-level ELM327 communication handler.
    Manages connection, initialization, and raw command sending.
    """

    BAUD_RATES = [38400, 9600, 115200, 57600, 19200]

    def __init__(self, port: Optional[str] = None, baudrate: int = 38400, timeout: float = 3.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection: Optional[serial.Serial] = None
        self.protocol: Optional[str] = None
        self.elm_version: Optional[str] = None

    @staticmethod
    def find_ports() -> List[str]:
        """Find and rank potential ELM327 USB serial ports."""
        ranked: List[tuple[int, str]] = []

        for p in serial.tools.list_ports.comports():
            dev = (p.device or "").lower()
            desc = (p.description or "").lower()

            # Skip common non-OBD ports
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
        """Establish connection to ELM327 adapter."""
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
            time.sleep(0.5)

            if not self._initialize():
                raise ConnectionError("ELM327 initialization failed")

            return True

        except serial.SerialException as e:
            raise ConnectionError(f"Serial port error: {e}")

    def _initialize(self) -> bool:
        """Initialize ELM327 with standard settings."""
        # Reset adapter
        resp = self.send_raw("ATZ", delay=1.5)
        self.elm_version = self._extract_version(resp) or "unknown"

        # Basic configuration
        self.send_raw("ATE0", delay=0.2)   # Echo off
        self.send_raw("ATL0", delay=0.2)   # Linefeeds off
        self.send_raw("ATS0", delay=0.2)   # Spaces off
        self.send_raw("ATH0", delay=0.2)   # Headers off

        # Helps many clones on real cars
        self.send_raw("ATAT1", delay=0.2)  # Adaptive timing on (if supported)
        self.send_raw("ATSP0", delay=0.5)  # Auto protocol

        return True

    @staticmethod
    def _extract_version(response: str) -> Optional[str]:
        """
        Attempt to extract a human-ish version string from ATZ response.
        Many clones respond with something like:
          'ELM327 v1.5'
          'ELM327 v2.1'
          or random banner text.
        """
        s = response.strip()
        if not s:
            return None

        # Common patterns
        m = re.search(r"(ELM327\s*v?\s*[\w\.]+)", s, re.IGNORECASE)
        if m:
            return m.group(1).strip()

        # Fallback: first 40 chars of banner
        return s[:40].strip() if s else None

    def send_raw(self, command: str, delay: float = 0.5) -> str:
        """Send raw command to ELM327 and return response (without the '>' prompt)."""
        if not self.connection:
            raise ConnectionError("Not connected to ELM327")

        try:
            # Clear buffers
            self.connection.reset_input_buffer()
            self.connection.reset_output_buffer()

            # Send
            self.connection.write(f"{command}\r".encode("ascii", errors="ignore"))
            time.sleep(delay)

            response = ""
            start_time = time.time()

            while True:
                if self.connection.in_waiting > 0:
                    ch = self.connection.read(1).decode("utf-8", errors="ignore")
                    if ch == ">":
                        break
                    response += ch
                elif time.time() - start_time > self.timeout:
                    break
                else:
                    time.sleep(0.02)

            # Normalize whitespace
            response = response.replace("\r", "\n")
            lines = [ln.strip() for ln in response.split("\n") if ln.strip()]
            return " ".join(lines)

        except Exception as e:
            raise IOError(f"Communication error: {e}")

    def send_obd(self, command: str) -> str:
        """Send OBD command and return cleaned response string (hex, no spaces)."""
        resp = self.send_raw(command, delay=1.0)
        up = resp.upper()

        if "NO DATA" in up:
            return "NO DATA"
        if "UNABLE TO CONNECT" in up:
            return "NO CONNECT"
        if "ERROR" in up:
            return "ERROR"
        if "?" in up:
            return "INVALID"

        # Keep only hex characters (many clones include stray text)
        hex_only = "".join(ch for ch in up if ch in "0123456789ABCDEF")
        return hex_only

    def test_vehicle_connection(self) -> bool:
        """Test if vehicle ECU is responding (Mode 01 PID 00)."""
        response = self.send_obd("0100")
        # Expect a response containing 41 00 ... (hex-only already)
        return "4100" in response

    def get_protocol(self) -> str:
        """Get the current OBD protocol in use."""
        resp = self.send_raw("ATDPN", delay=0.3).strip().upper()

        # ATDPN often returns:
        #   "A6" meaning auto + protocol 6
        #   "6" meaning protocol 6
        # We want the protocol code (single hex digit/letter).
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
        """Close the serial connection."""
        if self.connection:
            try:
                self.connection.close()
            finally:
                self.connection = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
