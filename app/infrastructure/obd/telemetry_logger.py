from __future__ import annotations

from typing import Any, Dict

from obd.logger import SessionLogger

from app.domain.ports import TelemetryLoggerFactory, TelemetryLoggerPort
from app.infrastructure.persistence.data_paths import logs_dir


class TelemetryLoggerAdapter(TelemetryLoggerPort):
    def __init__(self, logger: SessionLogger) -> None:
        self._logger = logger

    def start_session(self, format: str = "csv") -> str:
        path = self._logger.start_session(format=format)
        return str(path)

    def log_readings(self, readings: Dict[str, Any]) -> None:
        self._logger.log_readings(readings)

    def end_session(self) -> Dict[str, Any]:
        return self._logger.end_session()


class TelemetryLoggerFactoryImpl(TelemetryLoggerFactory):
    def create(self) -> TelemetryLoggerPort:
        logger = SessionLogger(str(logs_dir()))
        return TelemetryLoggerAdapter(logger)
