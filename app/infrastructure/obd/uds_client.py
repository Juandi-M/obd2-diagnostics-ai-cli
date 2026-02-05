from __future__ import annotations

from typing import Any, Dict

from obd.uds.client import UdsClient
from obd.uds.exceptions import UdsNegativeResponse, UdsResponseError
from obd.uds.modules import module_map as obd_module_map

from app.domain.entities import UdsError
from app.domain.ports import UdsClientFactory, UdsClientPort


class UdsClientAdapter(UdsClientPort):
    def __init__(self, client: UdsClient) -> None:
        self._client = client

    def read_did(self, brand: str, did: str) -> Dict[str, Any]:
        try:
            return self._client.read_did(brand, did)
        except (UdsNegativeResponse, UdsResponseError) as exc:
            raise UdsError(str(exc)) from exc

    def send_raw(self, service_id: int, data: bytes, *, raise_on_negative: bool = False) -> bytes:
        try:
            return self._client.send_raw(service_id, data, raise_on_negative=raise_on_negative)
        except (UdsNegativeResponse, UdsResponseError) as exc:
            raise UdsError(str(exc)) from exc


class UdsClientFactoryImpl(UdsClientFactory):
    def create(self, transport: Any, brand: str, module_entry: Dict[str, Any]) -> UdsClientPort:
        entry = dict(module_entry or {})
        protocol = str(entry.get("protocol") or "6")
        name = entry.get("name")
        tx_id = entry.get("tx_id")
        rx_id = entry.get("rx_id")
        if name:
            client = UdsClient.from_module(transport, brand, name, protocol=protocol)
        else:
            client = UdsClient(transport, tx_id=tx_id or "7E0", rx_id=rx_id or "7E8", protocol=protocol)
        return UdsClientAdapter(client)

    def module_map(self, brand: str) -> Dict[str, Dict[str, str]]:
        return {key: dict(value) for key, value in obd_module_map(brand).items()}
