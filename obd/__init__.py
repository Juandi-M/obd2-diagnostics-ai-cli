# obd/__init__.py
from .elm.elm327 import ELM327
from .elm.errors import CommunicationError, DeviceDisconnectedError

from .dtc import DTCDatabase, DTCInfo, decode_dtc_bytes, parse_dtc_response
from .pids import (
    OBDPid,
    PIDS,
    decode_pid_response,
    get_pid_info,
    list_available_pids,
    DIAGNOSTIC_PIDS,
    TEMPERATURE_PIDS,
    THROTTLE_PIDS,
)

from .obd2 import OBDScanner, OBD2Scanner

__all__ = [
    "ELM327",
    "CommunicationError",
    "DeviceDisconnectedError",
    "DTCDatabase",
    "DTCInfo",
    "decode_dtc_bytes",
    "parse_dtc_response",
    "OBDPid",
    "PIDS",
    "decode_pid_response",
    "get_pid_info",
    "list_available_pids",
    "DIAGNOSTIC_PIDS",
    "TEMPERATURE_PIDS",
    "THROTTLE_PIDS",
    "OBD2Scanner",
]
__version__ = "1.0.0"   # Example version number