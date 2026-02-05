from __future__ import annotations

from typing import Any, Dict

from app.domain.ports import UdsDiscoveryPort
from app.application.state import AppState


class UdsDiscoveryService:
    def __init__(self, state: AppState, discovery: UdsDiscoveryPort) -> None:
        self.state = state
        self.discovery = discovery

    def discover(self, options: Dict[str, Any]) -> Dict[str, Any]:
        scanner = self.state.ensure_scanner()
        return self.discovery.discover(scanner, options)
