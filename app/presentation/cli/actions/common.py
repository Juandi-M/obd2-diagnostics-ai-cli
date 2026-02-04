from __future__ import annotations

from typing import Optional, Union

from app.presentation.cli.i18n import t
from app.application.state import AppState
from app.presentation.cli.actions.connect import connect_vehicle
from app.domain.ports import KLineScannerPort, ScannerPort


def require_connected_scanner(
    state: AppState,
) -> Optional[Union[ScannerPort, KLineScannerPort]]:
    scanner = state.active_scanner()
    if not scanner:
        connected = connect_vehicle(state, auto=True)
        if not connected:
            print(f"\n  ❌ {t('not_connected')}")
            return None
        scanner = state.active_scanner()
    return scanner
