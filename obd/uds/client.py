from __future__ import annotations

from typing import Any, Dict, Optional

from ..elm import ELM327
from .decoder import decode_did_value
from .dids import find_did, find_did_by_name
from .routines import find_routine
from .services import UdsService
from .transport import UdsTransport
from .exceptions import UdsNegativeResponse, UdsResponseError


def _to_did_bytes(did: str | int) -> bytes:
    if isinstance(did, int):
        return did.to_bytes(2, byteorder="big")
    cleaned = did.strip().replace("0x", "").replace(" ", "")
    return int(cleaned, 16).to_bytes(2, byteorder="big")


def _to_hex_bytes(value: str) -> bytes:
    cleaned = value.strip().replace("0x", "").replace(" ", "")
    return bytes.fromhex(cleaned)


class UdsClient:
    def __init__(
        self,
        elm: ELM327,
        tx_id: str = "7E0",
        rx_id: str = "7E8",
        protocol: str = "6",
    ):
        self.transport = UdsTransport(elm, tx_id=tx_id, rx_id=rx_id, protocol=protocol)
        self._configured = False

    def configure(self) -> None:
        self.transport.configure()
        self._configured = True

    def _ensure_configured(self) -> None:
        if not self._configured:
            self.configure()

    def _send_and_expect(self, service_id: int, data: bytes) -> bytes:
        self._ensure_configured()
        request = UdsService.build_request(service_id, data)
        response = self.transport.send(request)

        if not response:
            raise UdsResponseError("Empty UDS response")

        if UdsService.is_negative_response(response):
            svc, nrc = UdsService.parse_negative(response)
            raise UdsNegativeResponse(svc, nrc)

        expected = UdsService.positive_response(service_id)
        if response[0] != expected:
            raise UdsResponseError(
                f"Unexpected response SID 0x{response[0]:02X} (expected 0x{expected:02X})"
            )

        return response

    def _expect_prefix(self, response: bytes, prefixes: list[bytes]) -> None:
        for prefix in prefixes:
            if response.startswith(prefix):
                return
        expected = ", ".join(p.hex().upper() for p in prefixes)
        raise UdsResponseError(f"Unexpected response prefix (expected one of: {expected})")

    def diagnostic_session(self, session_type: int = 0x03) -> Dict[str, Any]:
        """
        Enter diagnostic session (0x10).
        session_type 0x03 = extended session (common for service actions).
        """
        response = self._send_and_expect(0x10, bytes([session_type]))
        return {"session": session_type, "response": response.hex().upper()}

    def tester_present(self, subfunction: int = 0x00) -> Dict[str, Any]:
        """
        Keep session alive (0x3E). Some ECUs require this during long routines.
        """
        response = self._send_and_expect(0x3E, bytes([subfunction]))
        return {"response": response.hex().upper()}

    def ecu_reset(self, reset_type: int = 0x01) -> Dict[str, Any]:
        """
        ECU reset (0x11). reset_type 0x01 = hard reset, 0x03 = soft reset.
        """
        response = self._send_and_expect(0x11, bytes([reset_type]))
        return {"reset_type": reset_type, "response": response.hex().upper()}

    def clear_dtc(self, group: bytes = b"\xFF\xFF\xFF") -> Dict[str, Any]:
        """
        Clear DTCs (0x14). group defaults to all groups (0xFFFFFF).
        """
        response = self._send_and_expect(0x14, group)
        return {"response": response.hex().upper()}

    def security_access(self, level: int, key: bytes) -> Dict[str, Any]:
        """
        Security access (0x27).
        NOTE: Seed/key algorithm is OEM-specific and must be implemented per brand.
        """
        response = self._send_and_expect(0x27, bytes([level]) + key)
        return {"response": response.hex().upper()}

    def write_data_by_identifier(self, did: str | int, data: bytes) -> Dict[str, Any]:
        """
        WriteDataByIdentifier (0x2E).
        NOTE: Use only with known-good DIDs and payloads from reverse engineering.
        """
        did_bytes = _to_did_bytes(did)
        request = did_bytes + data
        response = self._send_and_expect(0x2E, request)
        expected_prefix = bytes([0x6E]) + did_bytes
        self._expect_prefix(response, [expected_prefix])
        return {"did": did_bytes.hex().upper(), "response": response.hex().upper()}

    def read_did(self, brand: str, did: str | int) -> Dict[str, Any]:
        entry = find_did(brand, f"{int(did):04X}" if isinstance(did, int) else did)
        did_bytes = _to_did_bytes(did)
        response = self._send_and_expect(0x22, did_bytes)

        if len(response) < 3:
            raise UdsResponseError("Response too short for DID read")

        resp_did = response[1:3]
        data = response[3:]

        info = {
            "did": f"{int.from_bytes(resp_did, 'big'):04X}",
            "raw": data.hex().upper(),
        }
        if entry:
            info["name"] = entry.get("name")
            info["value"] = decode_did_value(entry, data)
        return info

    def read_did_named(self, brand: str, name: str) -> Optional[Dict[str, Any]]:
        entry = find_did_by_name(brand, name)
        if not entry:
            return None
        return self.read_did(brand, entry["did"])

    def routine_control(
        self,
        brand: str,
        routine_name: str,
        *,
        subfunction: int = 0x01,
        payload_hex: str = "",
    ) -> Dict[str, Any]:
        routine = find_routine(brand, routine_name)
        if not routine:
            raise UdsResponseError(f"Unknown routine: {routine_name}")

        routine_id = int(routine["routine_id"], 16)
        data = bytes([subfunction]) + routine_id.to_bytes(2, "big") + _to_hex_bytes(payload_hex)
        response = self._send_and_expect(0x31, data)

        return {
            "routine": routine_name,
            "routine_id": routine["routine_id"],
            "status": response[3:].hex().upper() if len(response) > 3 else "",
        }
