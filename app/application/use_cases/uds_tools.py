from __future__ import annotations

from typing import Any, Dict

from app.application.state import AppState
from app.domain.entities import NotConnectedError, UdsError
from app.domain.ports import UdsClientFactory, UdsClientPort


class UdsToolsService:
    def __init__(self, state: AppState, factory: UdsClientFactory) -> None:
        self.state = state
        self.factory = factory

    def module_map(self, brand: str) -> Dict[str, Dict[str, str]]:
        return self.factory.module_map(brand)

    def build_client(self, brand: str, module_entry: Dict[str, Any]) -> UdsClientPort:
        scanner = self.state.active_scanner()
        if not scanner:
            raise NotConnectedError("Not connected to vehicle")
        if getattr(scanner, "is_kline", False):
            raise UdsError("UDS not supported on K-Line scanners")
        transport = scanner.get_transport()
        return self.factory.create(transport, brand, module_entry)
