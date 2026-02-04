from __future__ import annotations

from app.domain.ports import DataPathPort


class DataPathService:
    def __init__(self, port: DataPathPort) -> None:
        self.port = port

    def raw_log_path(self) -> str:
        return self.port.raw_log_path()
