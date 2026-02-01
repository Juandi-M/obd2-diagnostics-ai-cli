from __future__ import annotations

from typing import Optional

from obd import OBDScanner

from app.i18n import t


def require_connected_scanner(scanner: Optional[OBDScanner]) -> Optional[OBDScanner]:
    if not scanner or not scanner.is_connected:
        print(f"\n  ❌ {t('not_connected')}")
        return None
    return scanner
