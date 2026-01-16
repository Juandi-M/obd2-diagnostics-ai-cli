"""
OBD-II Scanner
==============
High-level scanner interface for vehicle diagnostics.
Includes robust error handling for disconnections.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import time
from typing import Optional, Dict, List, Tuple

from .elm327 import ELM327, DeviceDisconnectedError, CommunicationError
from .pids import PIDS, decode_pid_response, DIAGNOSTIC_PIDS
from .dtc import DTCDatabase, parse_dtc_response, decode_dtc_bytes
from .utils import cr_now

from .obd_parse import (
    group_by_ecu,
    merge_payloads,
    find_obd_response_payload,
    extract_ascii_from_hex_tokens,
    is_valid_vin,
)


class ScannerError(Exception):
    pass


class NotConnectedError(ScannerError):
    pass


class ConnectionLostError(ScannerError):
    pass


@dataclass
class SensorReading:
    name: str
    value: float
    unit: str
    pid: str
    raw_hex: str
    timestamp: datetime = field(default_factory=cr_now)

    @property
    def timestamp_str(self) -> str:
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class DiagnosticCode:
    code: str
    description: str
    status: str  # "stored", "pending", "permanent"
    timestamp: datetime = field(default_factory=cr_now)

    @property
    def timestamp_str(self) -> str:
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class ReadinessStatus:
    monitor_name: str
    available: bool
    complete: bool

    @property
    def status_str(self) -> str:
        if not self.available:
            return "N/A"
        return "Complete" if self.complete else "Incomplete"


@dataclass
class FreezeFrameData:
    dtc_code: str
    readings: Dict[str, SensorReading]
    timestamp: datetime = field(default_factory=cr_now)


class OBDScanner:
    ERROR_RESPONSES = {"NO DATA", "ERROR", "NO CONNECT", "INVALID", "DISCONNECTED"}

    # ECU preference order for CAN (common)
    ECU_PREFER = [
        "7E8", "7E0", "7E9", "7E1", "7EA", "7E2", "7EB", "7E3",
        "7EC", "7E4", "7ED", "7E5", "7EE", "7E6", "7EF", "7E7"
    ]

    def __init__(self, port: Optional[str] = None, baudrate: int = 38400, manufacturer: Optional[str] = None):
        self.elm = ELM327(port=port, baudrate=baudrate)
        self.dtc_db = DTCDatabase(manufacturer=manufacturer)
        self._connected = False

    def connect(self) -> bool:
        self.elm.connect()

        # Proactive: try to lock into a working protocol (safe to fail)
        try:
            self.elm.negotiate_protocol()
        except Exception:
            pass

        if not self.elm.test_vehicle_connection():
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

    def _is_error_response(self, response: str) -> bool:
        return response in self.ERROR_RESPONSES

    def set_manufacturer(self, manufacturer: str):
        self.dtc_db.set_manufacturer(manufacturer)

    # =========================================================================
    # Stage 1: Retry wrapper for raw lines (THIS is the one that matters)
    # =========================================================================
    def _send_obd_lines_retry(self, command: str, retries: int = 1) -> List[str]:
        last_lines: List[str] = []
        for attempt in range(retries + 1):
            try:
                lines = self.elm.send_obd_lines(command)
                last_lines = lines
                joined = " ".join(lines).upper()

                # If it doesn't look like an error, accept it
                if not any(err in joined for err in ["NO DATA", "UNABLE TO CONNECT", "ERROR", "STOPPED", "BUS", "CAN ERROR", "?", "BUFFER FULL"]):

                    return lines

            except DeviceDisconnectedError:
                self._handle_disconnection()
                raise ConnectionLostError("Device disconnected")

            # small backoff
            if attempt < retries:
                time.sleep(0.15)

        return last_lines

    # =========================================================================
    # Stage 1 robust helper
    # =========================================================================
    def _obd_query_payload(self, command: str, expected_prefix: List[str]) -> Optional[Tuple[str, List[str]]]:
        """
        Raw-lines -> group by ECU -> merge payload -> find prefix.
        Prefers Engine ECU on CAN if present.
        """
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

    # =========================================================================
    # DTC Methods
    # =========================================================================

    def read_dtcs(self) -> List[DiagnosticCode]:
        self._check_connected()

        dtcs: List[DiagnosticCode] = []
        read_time = cr_now()

        try:
            for mode, status in [("03", "stored"), ("07", "pending"), ("0A", "permanent")]:
                lines = self._send_obd_lines_retry(mode, retries=1)
                joined = " ".join(lines).upper()

                if any(err in joined for err in ["NO DATA", "UNABLE TO CONNECT", "ERROR", "?"]):
                    continue

                # Keep compatibility with parse_dtc_response() but feed it cleaner hex
                hex_only = "".join(ch for ch in joined if ch in "0123456789ABCDEF")
                if not hex_only:
                    continue

                for code in parse_dtc_response(hex_only, mode):
                    if not any(d.code == code for d in dtcs):
                        dtcs.append(DiagnosticCode(
                            code=code,
                            description=self.dtc_db.get_description(code),
                            status=status,
                            timestamp=read_time,
                        ))

        except DeviceDisconnectedError:
            self._handle_disconnection()
            raise ConnectionLostError("Device disconnected")
        except CommunicationError as e:
            raise ScannerError(f"Communication error: {e}")

        return dtcs

    def clear_dtcs(self) -> bool:
        self._check_connected()
        try:
            response = self.elm.send_obd("04")
            if response == "DISCONNECTED":
                self._handle_disconnection()
                raise ConnectionLostError("Device disconnected")
            return "44" in response.upper()
        except DeviceDisconnectedError:
            self._handle_disconnection()
            raise ConnectionLostError("Device disconnected")

    # =========================================================================
    # Live Data Methods
    # =========================================================================

    def read_pid(self, pid: str) -> Optional[SensorReading]:
        self._check_connected()

        pid = pid.upper()
        if pid not in PIDS:
            return None

        pid_info = PIDS[pid]

        found = self._obd_query_payload(f"01{pid}", expected_prefix=["41", pid])
        if not found:
            return None

        ecu, payload = found
        if len(payload) < 2:
            return None

        data_tokens = payload[2:]  # drop 41 + PID
        data_hex = "".join(data_tokens)

        value = decode_pid_response(pid, data_hex)
        if value is None:
            return None

        return SensorReading(
            name=pid_info.name,
            value=round(float(value), 2),
            unit=pid_info.unit,
            pid=pid,
            raw_hex=data_hex,
            timestamp=cr_now(),
        )

    def read_live_data(self, pids: Optional[List[str]] = None) -> Dict[str, SensorReading]:
        if pids is None:
            pids = DIAGNOSTIC_PIDS

        results: Dict[str, SensorReading] = {}
        for pid in pids:
            try:
                reading = self.read_pid(pid)
                if reading:
                    results[reading.pid] = reading
            except ConnectionLostError:
                raise
            except Exception:
                continue
        return results

    # =========================================================================
    # Freeze Frame (Mode 02)
    # =========================================================================

    def read_freeze_frame(self, frame_number: int = 0) -> Optional[FreezeFrameData]:
        self._check_connected()

        try:
            found = self._obd_query_payload(f"0202{frame_number:02X}", expected_prefix=["42", "02"])

            dtc_code = "Unknown"
            if found:
                ecu, payload = found
                if len(payload) >= 5:
                    dtc_hex = "".join(payload[3:5])
                    if len(dtc_hex) >= 4:
                        try:
                            dtc_code = decode_dtc_bytes(dtc_hex)
                        except Exception:
                            dtc_code = "Unknown"

            freeze_pids = ["04", "05", "06", "07", "0B", "0C", "0D", "0E", "0F", "11"]
            readings: Dict[str, SensorReading] = {}

            for pid in freeze_pids:
                if pid not in PIDS:
                    continue

                pid_info = PIDS[pid]
                found = self._obd_query_payload(f"02{pid}{frame_number:02X}", expected_prefix=["42", pid])
                if not found:
                    continue

                ecu, payload = found
                if len(payload) < 4:
                    continue

                data_tokens = payload[3:]  # drop 42, pid, frame
                data_hex = "".join(data_tokens)

                value = decode_pid_response(pid, data_hex)
                if value is not None:
                    readings[pid] = SensorReading(
                        name=pid_info.name,
                        value=round(float(value), 2),
                        unit=pid_info.unit,
                        pid=pid,
                        raw_hex=data_hex,
                        timestamp=cr_now(),
                    )

            if not readings:
                return None

            return FreezeFrameData(
                dtc_code=dtc_code,
                readings=readings,
                timestamp=cr_now(),
            )

        except DeviceDisconnectedError:
            self._handle_disconnection()
            raise ConnectionLostError("Device disconnected")

    # =========================================================================
    # Readiness Monitors (Mode 01, PID 01)
    # =========================================================================

    def read_readiness(self) -> Dict[str, ReadinessStatus]:
        self._check_connected()

        found = self._obd_query_payload("0101", expected_prefix=["41", "01"])
        if not found:
            return {}

        ecu, payload = found
        if len(payload) < 6:
            return {}

        try:
            A = int(payload[2], 16)
            B = int(payload[3], 16)
            C = int(payload[4], 16)
            D = int(payload[5], 16)
        except ValueError:
            return {}

        monitors: Dict[str, ReadinessStatus] = {}

        # MIL
        mil_on = bool(A & 0x80)
        monitors["MIL (Check Engine Light)"] = ReadinessStatus("MIL (Check Engine Light)", True, not mil_on)

        # Spark vs compression
        is_spark = not bool(B & 0x08)

        if is_spark:
            cont = [("Misfire", 0), ("Fuel System", 1), ("Components", 2)]
            for name, bit in cont:
                supported = bool(B & (1 << bit))
                incomplete = bool(C & (1 << bit))
                monitors[name] = ReadinessStatus(name, supported, (not incomplete) if supported else False)

            noncont = [
                ("Catalyst", ("B", 4), 0),
                ("Heated Catalyst", ("B", 5), 1),
                ("Evaporative System", ("B", 6), 2),
                ("Secondary Air", ("B", 7), 3),
                ("A/C Refrigerant", ("C", 3), 4),
                ("Oxygen Sensor", ("C", 4), 5),
                ("Oxygen Sensor Heater", ("C", 5), 6),
                ("EGR System", ("C", 6), 7),
            ]
            for name, (src, bit), d_bit in noncont:
                supported = bool((B if src == "B" else C) & (1 << bit))
                incomplete = bool(D & (1 << d_bit))
                monitors[name] = ReadinessStatus(name, supported, (not incomplete) if supported else False)

        else:
            diesel = [
                ("NMHC Catalyst", ("C", 0), 0),
                ("NOx/SCR Aftertreatment", ("C", 1), 1),
                ("Boost Pressure", ("C", 3), 3),
                ("Exhaust Gas Sensor", ("C", 5), 5),
                ("PM Filter", ("C", 6), 6),
                ("EGR/VVT System", ("C", 7), 7),
            ]
            for name, (src, bit), d_bit in diesel:
                supported = bool(C & (1 << bit))
                incomplete = bool(D & (1 << d_bit))
                monitors[name] = ReadinessStatus(name, supported, (not incomplete) if supported else False)

        return monitors

    def get_mil_status(self) -> Tuple[bool, int]:
        self._check_connected()

        found = self._obd_query_payload("0101", expected_prefix=["41", "01"])
        if not found:
            return (False, 0)

        ecu, payload = found
        if len(payload) < 3:
            return (False, 0)

        try:
            A = int(payload[2], 16)
        except ValueError:
            return (False, 0)

        mil_on = bool(A & 0x80)
        dtc_count = A & 0x7F
        return (mil_on, dtc_count)

    # =========================================================================
    # Vehicle Info
    # =========================================================================

    def get_vehicle_info(self) -> Dict[str, str]:
        self._check_connected()

        info: Dict[str, str] = {}
        try:
            info["protocol"] = self.elm.get_protocol()
            info["elm_version"] = self.elm.elm_version or "unknown"
            info["headers_mode"] = "ON" if self.elm.headers_on else "OFF"

            found = self._obd_query_payload("0902", expected_prefix=["49", "02"])
            if found:
                ecu, payload = found
                vin_tokens = payload[3:] if len(payload) > 3 else []
                vin = extract_ascii_from_hex_tokens(vin_tokens).strip().upper()
                info["vin_raw"] = "".join(payload)
                if is_valid_vin(vin):
                    info["vin"] = vin

            mil_on, dtc_count = self.get_mil_status()
            info["mil_on"] = "Yes" if mil_on else "No"
            info["dtc_count"] = str(dtc_count)

        except DeviceDisconnectedError:
            self._handle_disconnection()
            raise ConnectionLostError("Device disconnected")

        return info

    # =========================================================================
    # Stage 1: Self test helper
    # =========================================================================

    def self_test(self) -> Dict[str, object]:
        self._check_connected()

        summary: Dict[str, object] = {"ok": True, "steps": {}, "ecu_counts": {}, "headers_mode": "ON" if self.elm.headers_on else "OFF"}

        def run(cmd: str, prefix: List[str], name: str):
            try:
                lines = self._send_obd_lines_retry(cmd, retries=1)
                grouped = group_by_ecu(lines, headers_on=self.elm.headers_on)
                summary["ecu_counts"][name] = len(grouped.keys())
                merged = merge_payloads(grouped, headers_on=self.elm.headers_on)
                found = find_obd_response_payload(merged, prefix, prefer_ecus=self.ECU_PREFER if self.elm.headers_on else None)
                summary["steps"][name] = {"cmd": cmd, "found": bool(found)}
                if not found:
                    summary["ok"] = False
            except Exception as e:
                summary["steps"][name] = {"cmd": cmd, "error": str(e)}
                summary["ok"] = False

        run("0100", ["41", "00"], "mode01_pid00")
        run("0101", ["41", "01"], "mode01_pid01")
        run("0902", ["49", "02"], "mode09_pid02")

        try:
            info = self.get_vehicle_info()
            if "vin" in info:
                summary["vin_valid"] = True
                summary["vin"] = info["vin"]
            else:
                summary["vin_valid"] = False
        except Exception:
            summary["vin_valid"] = False
            summary["ok"] = False

        return summary

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
