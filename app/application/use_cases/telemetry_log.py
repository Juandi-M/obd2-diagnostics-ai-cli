from __future__ import annotations

from app.domain.ports import TelemetryLoggerFactory, TelemetryLoggerPort


class TelemetryLogService:
    def __init__(self, factory: TelemetryLoggerFactory) -> None:
        self.factory = factory

    def create_logger(self) -> TelemetryLoggerPort:
        return self.factory.create()
