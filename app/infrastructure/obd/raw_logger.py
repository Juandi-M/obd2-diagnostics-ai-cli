from __future__ import annotations

from typing import Any, Optional

from obd.rawlog import RawLogger
from app.infrastructure.persistence.data_paths import raw_log_path


class RawLoggerFactoryImpl:
    def create(self, enabled: bool) -> Optional[Any]:
        if not enabled:
            return None
        return RawLogger(str(raw_log_path()))
