from __future__ import annotations

from typing import Dict, List

from ..elm import DeviceDisconnectedError
from .base import ConnectionLostError
from ..protocol import (
    extract_ascii_from_hex_tokens,
    is_valid_vin,
    strip_isotp_pci_from_payload,
)


class VehicleInfoMixin:
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

                cleaned = strip_isotp_pci_from_payload(payload)

                vin_tokens: List[str] = []
                for i in range(0, max(0, len(cleaned) - 3)):
                    if cleaned[i:i+3] == ["49", "02", "01"]:
                        vin_tokens = cleaned[i+3:]
                        break
                if not vin_tokens:
                    vin_tokens = cleaned[3:] if len(cleaned) > 3 else []

                vin = extract_ascii_from_hex_tokens(vin_tokens).strip().upper()
                info["vin_raw"] = "".join(payload)

                if len(vin) >= 17:
                    vin = vin[:17]

                if is_valid_vin(vin):
                    info["vin"] = vin
                    info["vin_ecu"] = ecu

            mil_on, dtc_count = self.get_mil_status()
            info["mil_on"] = "Yes" if mil_on else "No"
            info["dtc_count"] = str(dtc_count)

        except DeviceDisconnectedError:
            self._handle_disconnection()
            raise ConnectionLostError("Device disconnected")

        return info
