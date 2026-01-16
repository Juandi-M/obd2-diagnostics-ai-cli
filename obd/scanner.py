"""
OBD-II Scanner
==============
High-level scanner interface for vehicle diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List

from .elm327 import ELM327
from .pids import PIDS, decode_pid_response, DIAGNOSTIC_PIDS
from .dtc import DTCDatabase, parse_dtc_response

# Costa Rica timezone
CR_TZ = timezone(timedelta(hours=-6))


def cr_now() -> datetime:
    """Get current time in Costa Rica timezone."""
    return datetime.now(CR_TZ)


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
    """OBD-II Readiness Monitor Status."""
    monitor_name: str
    available: bool  # Is this monitor supported by the vehicle?
    complete: bool   # Has this monitor completed its self-test?
    
    @property
    def status_str(self) -> str:
        if not self.available:
            return "N/A"
        return "Complete" if self.complete else "Incomplete"


@dataclass
class FreezeFrameData:
    """Freeze frame data captured when a DTC was set."""
    dtc_code: str
    readings: Dict[str, SensorReading]
    timestamp: datetime = field(default_factory=cr_now)


class OBDScanner:
    """
    High-level OBD-II scanner interface.
    Provides easy-to-use methods for reading DTCs and live data.
    """

    def __init__(self, port: Optional[str] = None, baudrate: int = 38400):
        self.elm = ELM327(port=port, baudrate=baudrate)
        self.dtc_db = DTCDatabase()
        self._connected = False

    def connect(self) -> bool:
        """Connect to vehicle using current self.elm.port (or auto-select inside ELM)."""
        self.elm.connect()

        if not self.elm.test_vehicle_connection():
            self._connected = False
            raise ConnectionError("No response from vehicle ECU")

        self._connected = True
        return True

    def auto_connect(self) -> str:
        """
        Automatically find and connect to a working ELM327 adapter.
        Returns the port that worked.
        """
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
        self.elm.close()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # =========================================================================
    # DTC Methods
    # =========================================================================
    
    def read_dtcs(self) -> List[DiagnosticCode]:
        """Read all diagnostic trouble codes (stored, pending, permanent)."""
        if not self._connected:
            raise ConnectionError("Not connected to vehicle")

        dtcs: List[DiagnosticCode] = []
        read_time = cr_now()

        # Mode 03: Stored DTCs
        response = self.elm.send_obd("03")
        if response not in ["NO DATA", "ERROR", "NO CONNECT", "INVALID"]:
            for code in parse_dtc_response(response, "03"):
                dtcs.append(DiagnosticCode(
                    code=code,
                    description=self.dtc_db.get_description(code),
                    status="stored",
                    timestamp=read_time,
                ))

        # Mode 07: Pending DTCs
        response = self.elm.send_obd("07")
        if response not in ["NO DATA", "ERROR", "NO CONNECT", "INVALID"]:
            for code in parse_dtc_response(response, "07"):
                if not any(d.code == code for d in dtcs):
                    dtcs.append(DiagnosticCode(
                        code=code,
                        description=self.dtc_db.get_description(code),
                        status="pending",
                        timestamp=read_time,
                    ))

        # Mode 0A: Permanent DTCs (requires CAN protocol)
        response = self.elm.send_obd("0A")
        if response not in ["NO DATA", "ERROR", "NO CONNECT", "INVALID"]:
            for code in parse_dtc_response(response, "0A"):
                if not any(d.code == code for d in dtcs):
                    dtcs.append(DiagnosticCode(
                        code=code,
                        description=self.dtc_db.get_description(code),
                        status="permanent",
                        timestamp=read_time,
                    ))

        return dtcs

    def clear_dtcs(self) -> bool:
        """Clear all DTCs (Mode 04). WARNING: Resets readiness monitors!"""
        if not self._connected:
            raise ConnectionError("Not connected to vehicle")
        response = self.elm.send_obd("04")
        return "44" in response.upper()

    # =========================================================================
    # Live Data Methods
    # =========================================================================
    
    def read_pid(self, pid: str) -> Optional[SensorReading]:
        """Read a single PID value."""
        if not self._connected:
            raise ConnectionError("Not connected to vehicle")

        pid = pid.upper()
        if pid not in PIDS:
            return None

        pid_info = PIDS[pid]
        response = self.elm.send_obd(f"01{pid}")

        if response in ["NO DATA", "ERROR", "NO CONNECT", "INVALID"]:
            return None

        resp_u = response.upper()
        expected_header = f"41{pid}"
        if expected_header not in resp_u:
            return None

        idx = resp_u.find(expected_header) + len(expected_header)
        data_hex = resp_u[idx:]

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
        """Read multiple PIDs at once."""
        if pids is None:
            pids = DIAGNOSTIC_PIDS

        results: Dict[str, SensorReading] = {}
        for pid in pids:
            reading = self.read_pid(pid)
            if reading:
                results[reading.pid] = reading
        return results

    # =========================================================================
    # Freeze Frame (Mode 02)
    # =========================================================================
    
    def read_freeze_frame(self, frame_number: int = 0) -> Optional[FreezeFrameData]:
        """
        Read freeze frame data (Mode 02).
        
        Freeze frame captures sensor values at the moment a DTC was stored.
        This helps diagnose what conditions caused the fault.
        
        Args:
            frame_number: Which freeze frame to read (usually 0)
            
        Returns:
            FreezeFrameData with sensor readings, or None if no data
        """
        if not self._connected:
            raise ConnectionError("Not connected to vehicle")
        
        # First, check if there's a freeze frame DTC (Mode 02, PID 02)
        response = self.elm.send_obd(f"0202")
        
        if response in ["NO DATA", "ERROR", "NO CONNECT", "INVALID"]:
            return None
        
        # Parse the DTC from freeze frame
        # Response format: 42 02 XX XX (where XX XX is the DTC)
        resp_u = response.upper()
        dtc_code = "Unknown"
        
        if "4202" in resp_u:
            idx = resp_u.find("4202") + 4
            if len(resp_u) >= idx + 4:
                dtc_hex = resp_u[idx:idx+4]
                from .dtc import decode_dtc_bytes
                dtc_code = decode_dtc_bytes(dtc_hex)
        
        # Now read common freeze frame PIDs
        # Mode 02 uses same PIDs as Mode 01, but with frame number
        freeze_pids = ["04", "05", "06", "07", "0B", "0C", "0D", "0E", "0F", "11"]
        
        readings: Dict[str, SensorReading] = {}
        
        for pid in freeze_pids:
            if pid not in PIDS:
                continue
                
            pid_info = PIDS[pid]
            # Mode 02, PID, Frame number (as 2 hex digits)
            cmd = f"02{pid}{frame_number:02X}"
            response = self.elm.send_obd(cmd)
            
            if response in ["NO DATA", "ERROR", "NO CONNECT", "INVALID"]:
                continue
            
            resp_u = response.upper()
            expected_header = f"42{pid}"
            
            if expected_header not in resp_u:
                continue
            
            # Skip frame number byte in response
            idx = resp_u.find(expected_header) + 4 + 2  # +2 for frame number
            data_hex = resp_u[idx:]
            
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

    # =========================================================================
    # Readiness Monitors (Mode 01, PID 01)
    # =========================================================================
    
    def read_readiness(self) -> Dict[str, ReadinessStatus]:
        """
        Read OBD-II readiness monitor status (Mode 01, PID 01).
        
        Shows which emission system self-tests have completed.
        Important after clearing DTCs - some tests need specific drive cycles.
        
        Returns:
            Dictionary of monitor name -> ReadinessStatus
        """
        if not self._connected:
            raise ConnectionError("Not connected to vehicle")
        
        response = self.elm.send_obd("0101")
        
        if response in ["NO DATA", "ERROR", "NO CONNECT", "INVALID"]:
            return {}
        
        resp_u = response.upper()
        
        if "4101" not in resp_u:
            return {}
        
        idx = resp_u.find("4101") + 4
        data_hex = resp_u[idx:]
        
        if len(data_hex) < 8:  # Need 4 bytes (8 hex chars)
            return {}
        
        try:
            # Parse 4 bytes: A B C D
            byte_a = int(data_hex[0:2], 16)
            byte_b = int(data_hex[2:4], 16)
            byte_c = int(data_hex[4:6], 16)
            byte_d = int(data_hex[6:8], 16)
        except ValueError:
            return {}
        
        monitors: Dict[str, ReadinessStatus] = {}
        
        # Byte A, bit 7: MIL status (not a readiness monitor, but useful)
        mil_on = bool(byte_a & 0x80)
        monitors["MIL (Check Engine Light)"] = ReadinessStatus(
            monitor_name="MIL (Check Engine Light)",
            available=True,
            complete=not mil_on,  # "Complete" means light is OFF
        )
        
        # Byte A, bits 0-6: Number of DTCs
        dtc_count = byte_a & 0x7F
        
        # Byte B determines spark vs compression ignition
        is_spark_ignition = not bool(byte_b & 0x08)
        
        if is_spark_ignition:
            # Spark ignition (gasoline) monitors - Bytes B, C, D
            
            # Byte B - availability (bit set = available)
            # Byte C - completeness for continuous monitors (bit set = incomplete)
            # Byte D - completeness for non-continuous monitors (bit set = incomplete)
            
            # Continuous monitors (Byte B bits 0-2 available, Byte C bits 0-2 complete)
            continuous_monitors = [
                ("Misfire", 0),
                ("Fuel System", 1),
                ("Components", 2),
            ]
            
            for name, bit in continuous_monitors:
                available = bool(byte_b & (1 << bit))
                incomplete = bool(byte_c & (1 << bit))
                monitors[name] = ReadinessStatus(
                    monitor_name=name,
                    available=available,
                    complete=not incomplete if available else False,
                )
            
            # Non-continuous monitors (Byte B bits 4-7 available, Byte D bits 0-7 complete)
            non_continuous_monitors = [
                ("Catalyst", 0, 0),          # B bit 0, D bit 0
                ("Heated Catalyst", 1, 1),   # B bit 1, D bit 1
                ("Evaporative System", 2, 2),
                ("Secondary Air", 3, 3),
                ("A/C Refrigerant", 4, 4),
                ("Oxygen Sensor", 5, 5),
                ("Oxygen Sensor Heater", 6, 6),
                ("EGR System", 7, 7),
            ]
            
            for name, b_bit, d_bit in non_continuous_monitors:
                available = bool(byte_b & (1 << (b_bit + 4))) if b_bit < 4 else bool(byte_b & (1 << b_bit))
                # Adjust for actual bit positions in standard
                available = bool(byte_b & (1 << (4 + (d_bit if d_bit < 4 else d_bit - 4))))
                incomplete = bool(byte_d & (1 << d_bit))
                
                monitors[name] = ReadinessStatus(
                    monitor_name=name,
                    available=True,  # Simplified - assume available if we got here
                    complete=not incomplete,
                )
        
        else:
            # Compression ignition (diesel) monitors
            diesel_monitors = [
                ("NMHC Catalyst", 0),
                ("NOx/SCR Aftertreatment", 1),
                ("Boost Pressure", 3),
                ("Exhaust Gas Sensor", 5),
                ("PM Filter", 6),
                ("EGR/VVT System", 7),
            ]
            
            for name, bit in diesel_monitors:
                incomplete = bool(byte_d & (1 << bit))
                monitors[name] = ReadinessStatus(
                    monitor_name=name,
                    available=True,
                    complete=not incomplete,
                )
        
        return monitors
    
    def get_mil_status(self) -> tuple[bool, int]:
        """
        Quick check of MIL (Malfunction Indicator Lamp) status.
        
        Returns:
            Tuple of (mil_on: bool, dtc_count: int)
        """
        if not self._connected:
            raise ConnectionError("Not connected to vehicle")
        
        response = self.elm.send_obd("0101")
        
        if response in ["NO DATA", "ERROR", "NO CONNECT", "INVALID"]:
            return (False, 0)
        
        resp_u = response.upper()
        
        if "4101" not in resp_u:
            return (False, 0)
        
        idx = resp_u.find("4101") + 4
        data_hex = resp_u[idx:]
        
        if len(data_hex) < 2:
            return (False, 0)
        
        try:
            byte_a = int(data_hex[0:2], 16)
            mil_on = bool(byte_a & 0x80)
            dtc_count = byte_a & 0x7F
            return (mil_on, dtc_count)
        except ValueError:
            return (False, 0)

    # =========================================================================
    # Vehicle Info
    # =========================================================================
    
    def get_vehicle_info(self) -> Dict[str, str]:
        """Get basic vehicle/connection information."""
        info: Dict[str, str] = {}
        info["protocol"] = self.elm.get_protocol()
        info["elm_version"] = self.elm.elm_version or "unknown"

        # Try to get VIN
        response = self.elm.send_obd("0902")
        if response not in ["NO DATA", "ERROR", "NO CONNECT", "INVALID"]:
            info["vin_raw"] = response

        # MIL status
        mil_on, dtc_count = self.get_mil_status()
        info["mil_on"] = "Yes" if mil_on else "No"
        info["dtc_count"] = str(dtc_count)

        return info

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
