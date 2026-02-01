from __future__ import annotations

class UdsError(Exception):
    """Base exception for UDS module."""


class UdsTransportError(UdsError):
    """Transport-level failure (ELM, CAN, ISO-TP)."""


class UdsResponseError(UdsError):
    """Malformed or unexpected UDS response."""


class UdsNegativeResponse(UdsError):
    """Negative response from ECU (0x7F)."""

    def __init__(self, service_id: int, nrc: int, message: str | None = None):
        self.service_id = service_id
        self.nrc = nrc
        if message is None:
            message = f"Negative response: service 0x{service_id:02X}, NRC 0x{nrc:02X}"
        super().__init__(message)
