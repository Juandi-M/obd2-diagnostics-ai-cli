from __future__ import annotations

from typing import Optional, Union

from obd import OBDScanner
from obd.legacy_kline.adapter import LegacyKLineAdapter

from app_cli.i18n import t
from app_cli.state import AppState
from app_cli.actions.connect import connect_vehicle


def require_connected_scanner(
    state: AppState,
) -> Optional[Union[OBDScanner, LegacyKLineAdapter]]:
    scanner = state.active_scanner()
    if not scanner:
        connected = connect_vehicle(state, auto=True)
        if not connected:
            print(f"\n  ❌ {t('not_connected')}")
            return None
        scanner = state.active_scanner()
    return scanner
