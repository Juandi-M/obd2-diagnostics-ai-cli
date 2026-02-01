from __future__ import annotations

from typing import List, Optional

from ..elm import ELM327, CommunicationError, DeviceDisconnectedError
from ..protocol import group_by_ecu, merge_payloads
from .exceptions import UdsTransportError


def _hex_bytes(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)


def _tokens_to_bytes(tokens: List[str]) -> bytes:
    out = bytearray()
    for tok in tokens:
        if not tok:
            continue
        try:
            out.append(int(tok, 16))
        except ValueError:
            continue
    return bytes(out)


class UdsTransport:
    """
    Minimal CAN/ELM transport for UDS.

    Uses ATSP6 (11-bit, 500k) by default and ATH1 headers.
    """

    def __init__(
        self,
        elm: ELM327,
        tx_id: str = "7E0",
        rx_id: str = "7E8",
        protocol: str = "6",
        headers_on: bool = True,
    ):
        self.elm = elm
        self.tx_id = tx_id.upper()
        self.rx_id = rx_id.upper()
        self.protocol = protocol
        self.headers_on = headers_on

    def configure(self) -> None:
        try:
            self.elm.send_raw_lines(f"ATSP{self.protocol}")
            self.elm.send_raw_lines("ATE0")
            self.elm.send_raw_lines("ATL0")
            self.elm.send_raw_lines("ATS0")
            self.elm.send_raw_lines("ATH1" if self.headers_on else "ATH0")
            self.elm.send_raw_lines(f"ATSH{self.tx_id}")
        except (CommunicationError, DeviceDisconnectedError) as exc:
            raise UdsTransportError(str(exc))

    def send(self, payload: bytes, timeout: Optional[float] = None) -> bytes:
        try:
            lines = self.elm.send_raw_lines(_hex_bytes(payload), timeout=timeout)
        except (CommunicationError, DeviceDisconnectedError) as exc:
            raise UdsTransportError(str(exc))

        grouped = group_by_ecu(lines, headers_on=self.headers_on)
        merged = merge_payloads(grouped, headers_on=self.headers_on)

        if self.headers_on:
            tokens = merged.get(self.rx_id) or next(iter(merged.values()), [])
        else:
            tokens = merged.get("NOHDR") or next(iter(merged.values()), [])

        return _tokens_to_bytes(tokens)
