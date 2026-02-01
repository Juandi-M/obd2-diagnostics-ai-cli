from __future__ import annotations

from dataclasses import dataclass

SERVICE_NAMES = {
    0x10: "Diagnostic Session Control",
    0x11: "ECU Reset",
    0x19: "Read DTC Information",
    0x22: "Read Data By Identifier",
    0x23: "Read Memory By Address",
    0x27: "Security Access",
    0x2E: "Write Data By Identifier",
    0x2F: "Input Output Control",
    0x31: "Routine Control",
    0x34: "Request Download",
    0x36: "Transfer Data",
    0x37: "Request Transfer Exit",
    0x3E: "Tester Present",
}

NEGATIVE_RESPONSE_SID = 0x7F


@dataclass(frozen=True)
class UdsService:
    service_id: int
    description: str

    @staticmethod
    def name(service_id: int) -> str:
        return SERVICE_NAMES.get(service_id, f"Unknown (0x{service_id:02X})")

    @staticmethod
    def positive_response(service_id: int) -> int:
        return (service_id + 0x40) & 0xFF

    @staticmethod
    def build_request(service_id: int, data: bytes = b"") -> bytes:
        return bytes([service_id]) + data

    @staticmethod
    def is_negative_response(payload: bytes) -> bool:
        return len(payload) >= 3 and payload[0] == NEGATIVE_RESPONSE_SID

    @staticmethod
    def parse_negative(payload: bytes) -> tuple[int, int]:
        if len(payload) < 3 or payload[0] != NEGATIVE_RESPONSE_SID:
            return (0x00, 0x00)
        return (payload[1], payload[2])
