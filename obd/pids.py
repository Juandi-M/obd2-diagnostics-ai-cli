"""
OBD-II PID Definitions
======================
Standard Parameter IDs and their decoding formulas.
Based on SAE J1979 standard.
"""

from dataclasses import dataclass
from typing import Callable, Optional, List


@dataclass
class OBDPid:
    """Represents an OBD-II Parameter ID."""
    pid: str
    name: str
    unit: str
    bytes: int
    formula: Callable
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: Optional[str] = None


# Mode 01 - Live Data PIDs
# These are the standard PIDs for reading real-time sensor data

PIDS = {
    # Engine Load and Performance
    "04": OBDPid(
        pid="04",
        name="Calculated Engine Load",
        unit="%",
        bytes=1,
        formula=lambda a: (a * 100) / 255,
        min_value=0,
        max_value=100,
        description="Indicates percentage of peak available torque"
    ),
    
    # Temperature Sensors
    "05": OBDPid(
        pid="05",
        name="Engine Coolant Temperature",
        unit="°C",
        bytes=1,
        formula=lambda a: a - 40,
        min_value=-40,
        max_value=215,
        description="Coolant temperature from ECT sensor"
    ),
    
    "0F": OBDPid(
        pid="0F",
        name="Intake Air Temperature",
        unit="°C",
        bytes=1,
        formula=lambda a: a - 40,
        min_value=-40,
        max_value=215,
        description="Air temperature entering the engine"
    ),
    
    "5C": OBDPid(
        pid="5C",
        name="Engine Oil Temperature",
        unit="°C",
        bytes=1,
        formula=lambda a: a - 40,
        min_value=-40,
        max_value=215,
        description="Oil temperature (if supported)"
    ),
    
    # Fuel Trims
    "06": OBDPid(
        pid="06",
        name="Short Term Fuel Trim - Bank 1",
        unit="%",
        bytes=1,
        formula=lambda a: (a - 128) * 100 / 128,
        min_value=-100,
        max_value=99.2,
        description="Immediate fuel adjustment (+ = adding fuel)"
    ),
    
    "07": OBDPid(
        pid="07",
        name="Long Term Fuel Trim - Bank 1",
        unit="%",
        bytes=1,
        formula=lambda a: (a - 128) * 100 / 128,
        min_value=-100,
        max_value=99.2,
        description="Learned fuel adjustment (+ = adding fuel)"
    ),
    
    "08": OBDPid(
        pid="08",
        name="Short Term Fuel Trim - Bank 2",
        unit="%",
        bytes=1,
        formula=lambda a: (a - 128) * 100 / 128,
        min_value=-100,
        max_value=99.2,
        description="Immediate fuel adjustment bank 2"
    ),
    
    "09": OBDPid(
        pid="09",
        name="Long Term Fuel Trim - Bank 2",
        unit="%",
        bytes=1,
        formula=lambda a: (a - 128) * 100 / 128,
        min_value=-100,
        max_value=99.2,
        description="Learned fuel adjustment bank 2"
    ),
    
    # Pressure Sensors
    "0A": OBDPid(
        pid="0A",
        name="Fuel Pressure",
        unit="kPa",
        bytes=1,
        formula=lambda a: a * 3,
        min_value=0,
        max_value=765,
        description="Fuel rail pressure (gauge)"
    ),
    
    "0B": OBDPid(
        pid="0B",
        name="Intake Manifold Pressure",
        unit="kPa",
        bytes=1,
        formula=lambda a: a,
        min_value=0,
        max_value=255,
        description="MAP sensor reading"
    ),
    
    # Engine Speed and Vehicle Speed
    "0C": OBDPid(
        pid="0C",
        name="Engine RPM",
        unit="rpm",
        bytes=2,
        formula=lambda a, b: ((a * 256) + b) / 4,
        min_value=0,
        max_value=16383.75,
        description="Current engine speed"
    ),
    
    "0D": OBDPid(
        pid="0D",
        name="Vehicle Speed",
        unit="km/h",
        bytes=1,
        formula=lambda a: a,
        min_value=0,
        max_value=255,
        description="Current vehicle speed"
    ),
    
    # Timing
    "0E": OBDPid(
        pid="0E",
        name="Timing Advance",
        unit="°",
        bytes=1,
        formula=lambda a: (a / 2) - 64,
        min_value=-64,
        max_value=63.5,
        description="Ignition timing advance for #1 cylinder"
    ),
    
    # MAF Sensor
    "10": OBDPid(
        pid="10",
        name="MAF Air Flow Rate",
        unit="g/s",
        bytes=2,
        formula=lambda a, b: ((a * 256) + b) / 100,
        min_value=0,
        max_value=655.35,
        description="Mass air flow sensor reading"
    ),
    
    # Throttle Position
    "11": OBDPid(
        pid="11",
        name="Throttle Position",
        unit="%",
        bytes=1,
        formula=lambda a: (a * 100) / 255,
        min_value=0,
        max_value=100,
        description="Absolute throttle position"
    ),
    
    "45": OBDPid(
        pid="45",
        name="Relative Throttle Position",
        unit="%",
        bytes=1,
        formula=lambda a: (a * 100) / 255,
        min_value=0,
        max_value=100,
        description="Relative throttle position"
    ),
    
    "47": OBDPid(
        pid="47",
        name="Absolute Throttle Position B",
        unit="%",
        bytes=1,
        formula=lambda a: (a * 100) / 255,
        min_value=0,
        max_value=100,
        description="Throttle position sensor B"
    ),
    
    "4C": OBDPid(
        pid="4C",
        name="Commanded Throttle Actuator",
        unit="%",
        bytes=1,
        formula=lambda a: (a * 100) / 255,
        min_value=0,
        max_value=100,
        description="Commanded throttle actuator position"
    ),
    
    # Accelerator Pedal Position
    "49": OBDPid(
        pid="49",
        name="Accelerator Pedal Position D",
        unit="%",
        bytes=1,
        formula=lambda a: (a * 100) / 255,
        min_value=0,
        max_value=100,
        description="Accelerator pedal position sensor D"
    ),
    
    "4A": OBDPid(
        pid="4A",
        name="Accelerator Pedal Position E",
        unit="%",
        bytes=1,
        formula=lambda a: (a * 100) / 255,
        min_value=0,
        max_value=100,
        description="Accelerator pedal position sensor E"
    ),
    
    # Run Time
    "1F": OBDPid(
        pid="1F",
        name="Run Time Since Engine Start",
        unit="sec",
        bytes=2,
        formula=lambda a, b: (a * 256) + b,
        min_value=0,
        max_value=65535,
        description="Time since engine start"
    ),
    
    # Fuel Level
    "2F": OBDPid(
        pid="2F",
        name="Fuel Tank Level",
        unit="%",
        bytes=1,
        formula=lambda a: (a * 100) / 255,
        min_value=0,
        max_value=100,
        description="Fuel tank level input"
    ),
    
    # Voltage
    "42": OBDPid(
        pid="42",
        name="Control Module Voltage",
        unit="V",
        bytes=2,
        formula=lambda a, b: ((a * 256) + b) / 1000,
        min_value=0,
        max_value=65.535,
        description="ECU supply voltage"
    ),
    
    # O2 Sensors
    "14": OBDPid(
        pid="14",
        name="O2 Sensor 1 Voltage",
        unit="V",
        bytes=2,
        formula=lambda a, b: a / 200,  # First byte is voltage
        min_value=0,
        max_value=1.275,
        description="Bank 1 Sensor 1 O2 voltage"
    ),
    
    "15": OBDPid(
        pid="15",
        name="O2 Sensor 2 Voltage",
        unit="V",
        bytes=2,
        formula=lambda a, b: a / 200,
        min_value=0,
        max_value=1.275,
        description="Bank 1 Sensor 2 O2 voltage"
    ),
}


# Diagnostic PIDs - commonly useful for troubleshooting
DIAGNOSTIC_PIDS = ["05", "0C", "0D", "11", "45", "49", "4A", "4C", "42", "0B", "06", "07"]

# Temperature PIDs
TEMPERATURE_PIDS = ["05", "0F", "5C"]

# Throttle-related PIDs - useful for ETC issues
THROTTLE_PIDS = ["11", "45", "47", "4C", "49", "4A"]


def decode_pid_response(pid: str, hex_data: str) -> Optional[float]:
    """
    Decode a PID response using its formula.
    
    Args:
        pid: The PID code (e.g., "05")
        hex_data: The hex data portion of the response
        
    Returns:
        Decoded value or None if decoding fails
    """
    if pid not in PIDS:
        return None
        
    pid_info = PIDS[pid]
    
    try:
        if pid_info.bytes == 1 and len(hex_data) >= 2:
            a = int(hex_data[0:2], 16)
            return pid_info.formula(a)
        elif pid_info.bytes == 2 and len(hex_data) >= 4:
            a = int(hex_data[0:2], 16)
            b = int(hex_data[2:4], 16)
            return pid_info.formula(a, b)
    except (ValueError, TypeError):
        pass
        
    return None


def get_pid_info(pid: str) -> Optional[OBDPid]:
    """Get PID information by code."""
    return PIDS.get(pid)


def list_available_pids() -> List[str]:
    """List all available PID codes."""
    return list(PIDS.keys())
