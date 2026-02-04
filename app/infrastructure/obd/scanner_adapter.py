from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from obd import OBDScanner, DTCDatabase, ELM327
from obd.obd2.base import ConnectionLostError as OBDConnectionLostError
from obd.obd2.base import NotConnectedError as OBDNotConnectedError
from obd.obd2.base import ScannerError as OBDScannerError
from obd.kline.adapter import KLineAdapter
from obd.kline.session import KLineSession
from obd.kline.profiles import ISO9141_2, KWP2000_5BAUD, KWP2000_FAST, td5_candidates
from obd.kline.config.errors import KLineDetectError, KLineError as OBDKLineError

from app.domain.ports import (
    ScannerPort,
    KLineScannerPort,
    ScannerFactory,
    KLineScannerFactory,
    DtcDatabaseFactory,
    DtcLookupPort,
)
from app.domain.entities import ConnectionLostError, NotConnectedError, ScannerError, KLineError
from app.infrastructure.obd.raw_logger import RawLoggerFactoryImpl


def _raise_domain_scanner_error(exc: Exception) -> None:
    if isinstance(exc, OBDNotConnectedError):
        raise NotConnectedError(str(exc)) from exc
    if isinstance(exc, OBDConnectionLostError):
        raise ConnectionLostError(str(exc)) from exc
    if isinstance(exc, OBDScannerError):
        raise ScannerError(str(exc)) from exc
    raise exc


def _raise_domain_kline_error(exc: Exception) -> None:
    if isinstance(exc, OBDKLineError):
        raise KLineError(str(exc)) from exc
    raise exc


class OBDScannerAdapter(ScannerPort):
    def __init__(self, scanner: OBDScanner) -> None:
        self._scanner = scanner

    @property
    def is_connected(self) -> bool:  # type: ignore[override]
        return self._scanner.is_connected

    def set_raw_logger(self, logger: Optional[Any]) -> None:
        self._scanner.elm.raw_logger = logger

    def set_port(self, port: str) -> None:
        self._scanner.elm.port = port

    def set_manufacturer(self, manufacturer: str) -> None:
        self._scanner.set_manufacturer(manufacturer)

    def connect(self) -> bool:
        try:
            return self._scanner.connect()
        except Exception as exc:
            _raise_domain_scanner_error(exc)
            raise

    def disconnect(self) -> None:
        try:
            self._scanner.disconnect()
        except Exception as exc:
            _raise_domain_scanner_error(exc)

    def get_transport(self) -> Any:
        return self._scanner.elm

    def debug_snapshot(self) -> Dict[str, Any]:
        elm = self._scanner.elm
        return {
            "elm_version": getattr(elm, "elm_version", None),
            "last_command": getattr(elm, "last_command", None),
            "last_response": " | ".join(getattr(elm, "last_lines", []) or []),
            "last_error": getattr(elm, "last_error", None),
            "last_duration_s": getattr(elm, "last_duration_s", None),
            "timeout": getattr(elm, "timeout", None),
        }

    def get_vehicle_info(self) -> Dict[str, Any]:
        try:
            return self._scanner.get_vehicle_info()
        except Exception as exc:
            _raise_domain_scanner_error(exc)
            raise

    def read_dtcs(self) -> List[Any]:
        try:
            return self._scanner.read_dtcs()
        except Exception as exc:
            _raise_domain_scanner_error(exc)
            raise

    def read_readiness(self) -> Dict[str, Any]:
        try:
            return self._scanner.read_readiness()
        except Exception as exc:
            _raise_domain_scanner_error(exc)
            raise

    def read_live_data(self, pids: Optional[List[str]] = None) -> Dict[str, Any]:
        try:
            if pids is None:
                return self._scanner.read_live_data()
            return self._scanner.read_live_data(pids)
        except Exception as exc:
            _raise_domain_scanner_error(exc)
            raise

    def read_freeze_frame(self) -> Dict[str, Any]:
        try:
            return self._scanner.read_freeze_frame()
        except Exception as exc:
            _raise_domain_scanner_error(exc)
            raise

    def clear_codes(self) -> bool:
        try:
            return self._scanner.clear_codes()
        except Exception as exc:
            _raise_domain_scanner_error(exc)
            raise


class KLineScannerAdapter(KLineScannerPort):
    def __init__(self, adapter: KLineAdapter) -> None:
        self._adapter = adapter

    @property
    def is_connected(self) -> bool:  # type: ignore[override]
        return self._adapter.is_connected

    @property
    def is_kline(self) -> bool:  # type: ignore[override]
        return True

    def set_raw_logger(self, logger: Optional[Any]) -> None:
        self._adapter.elm.raw_logger = logger

    def set_manufacturer(self, manufacturer: str) -> None:
        self._adapter.set_manufacturer(manufacturer)

    def disconnect(self) -> None:
        try:
            self._adapter.disconnect()
        except Exception as exc:
            _raise_domain_kline_error(exc)

    def read_dtcs(self, mode: str = "stored") -> Dict[str, Any]:
        try:
            return self._adapter.scanner.read_dtcs(mode=mode)
        except Exception as exc:
            _raise_domain_kline_error(exc)
            raise

    def clear_dtcs(self) -> Tuple[bool, Dict[str, Any]]:
        try:
            return self._adapter.scanner.clear_dtcs()
        except Exception as exc:
            _raise_domain_kline_error(exc)
            raise

    def read_pid(self, pid: str) -> Dict[str, Any]:
        try:
            return self._adapter.scanner.read_pid(pid)
        except Exception as exc:
            _raise_domain_kline_error(exc)
            raise


class OBDScannerFactory(ScannerFactory):
    def __init__(self, raw_logger_factory: Optional[RawLoggerFactoryImpl] = None) -> None:
        self.raw_logger_factory = raw_logger_factory or RawLoggerFactoryImpl()

    def create(self, manufacturer: Optional[str]) -> ScannerPort:
        scanner = OBDScanner(
            manufacturer=manufacturer,
            raw_logger=self.raw_logger_factory.create(False),
        )
        return OBDScannerAdapter(scanner)


class KLineScannerFactoryImpl(KLineScannerFactory):
    def create(self, port: str, manufacturer: Optional[str]) -> KLineScannerPort:
        session = KLineSession(port=port)
        adapter = KLineAdapter(session, manufacturer=manufacturer)
        return KLineScannerAdapter(adapter)

    def detect(
        self,
        port: str,
        manufacturer: Optional[str],
        raw_logger: Optional[Any] = None,
    ) -> Tuple[Optional[KLineScannerPort], Optional[Dict[str, Any]], Optional[Exception]]:
        try:
            elm = ELM327(port=port, raw_logger=raw_logger)
            elm.connect()
        except Exception as exc:
            return None, None, exc

        candidates = [KWP2000_5BAUD, KWP2000_FAST, ISO9141_2]
        if manufacturer == "landrover":
            candidates = candidates + td5_candidates()

        try:
            session = KLineSession.auto(elm, candidates=candidates)
            adapter = KLineAdapter(
                session,
                manufacturer=manufacturer,
            )
            info = {
                "profile_name": session.info.profile_name,
                "reason": session.info.reason,
            }
            return KLineScannerAdapter(adapter), info, None
        except (KLineDetectError, OBDKLineError) as exc:
            try:
                elm.close()
            except Exception:
                pass
            return None, None, KLineError(str(exc))
        except Exception as exc:
            try:
                elm.close()
            except Exception:
                pass
            return None, None, exc


class DtcDatabaseAdapter(DtcLookupPort):
    def __init__(self, db: DTCDatabase) -> None:
        self._db = db

    @property
    def count(self) -> int:
        return getattr(self._db, "count", len(getattr(self._db, "codes", {}) or {}))

    @property
    def loaded_files(self) -> List[str]:
        return list(getattr(self._db, "loaded_files", []))

    def set_manufacturer(self, manufacturer: str) -> None:
        self._db.set_manufacturer(manufacturer)

    def lookup(self, code: str) -> Optional[Dict[str, Any]]:
        return self._db.lookup(code)

    def search(self, text: str) -> List[Dict[str, Any]]:
        return self._db.search(text)


class DtcDatabaseFactoryImpl(DtcDatabaseFactory):
    def create(self, manufacturer: Optional[str]) -> DtcLookupPort:
        return DtcDatabaseAdapter(DTCDatabase(manufacturer=manufacturer))
