from __future__ import annotations

from app.domain.ports import DataPathPort
from app.infrastructure.persistence.data_paths import raw_log_path


class DataPathAdapter(DataPathPort):
    def raw_log_path(self) -> str:
        return str(raw_log_path())
