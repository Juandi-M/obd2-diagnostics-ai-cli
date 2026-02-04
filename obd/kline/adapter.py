from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Sequence

from obd.obd2.base import NotConnectedError, ScannerError
from obd.obd2.models import DiagnosticCode, SensorReading, FreezeFrameData
from obd.pids.sets import DIAGNOSTIC_PIDS
from obd.utils import cr_now

from .scanner import KLineScanner
from .session import KLineSession


@dataclass
class KLineAdapter:
    session: KLineSession
    manufacturer: Optional[str] = None

    def __post_init__(self) -> None:
        self.scanner = KLineScanner(self.session, manufacturer=self.manufacturer)
        self.is_kline = True

    @property
    def elm(self):
        return self.session.elm

    @property
    def is_connected(self) -> bool:
        return bool(self.session.elm and self.session.elm.is_connected)

    def disconnect(self) -> None:
        self.session.close()

    def set_manufacturer(self, manufacturer: str) -> None:
        self.manufacturer = manufacturer
        self.scanner.manufacturer = manufacturer

    def _check_connected(self) -> None:
        if not self.is_connected:
            raise NotConnectedError("Not connected to vehicle")

    def get_vehicle_info(self) -> Dict[str, str]:
        self._check_connected()
        info: Dict[str, str] = {
            "protocol": "K-LINE",
            "elm_version": self.elm.elm_version or "unknown",
            "headers_mode": "N/A",
            "mil_on": "Unknown",
            "dtc_count": "unknown",
        }
        return info

    def read_dtcs(self) -> Sequence[DiagnosticCode]:
        self._check_connected()
        dtcs = []
        seen = set()
        read_time = cr_now()
        try:
            for mode, status in [("03", "stored"), ("07", "pending"), ("0A", "permanent")]:
                result = self.scanner.read_dtcs(mode=mode)
                for item in result.dtcs:
                    if item.code in seen:
                        continue
                    seen.add(item.code)
                    dtcs.append(
                        DiagnosticCode(
                            code=item.code,
                            description=item.description,
                            status=status,
                            timestamp=read_time,
                        )
                    )
        except Exception as exc:
            raise ScannerError(str(exc)) from exc
        return dtcs

    def clear_dtcs(self) -> bool:
        self._check_connected()
        try:
            ok, _ = self.scanner.clear_dtcs()
            return ok
        except Exception as exc:
            raise ScannerError(str(exc)) from exc

    def read_readiness(self) -> Dict[str, object]:
        self._check_connected()
        return {}

    def read_freeze_frame(self) -> Optional[FreezeFrameData]:
        self._check_connected()
        return None

    def read_live_data(
        self,
        pids: Optional[Sequence[str]] = None,
        *,
        round_to: int = 2,
        dedupe: bool = True,
        stop_on_error: bool = False,
    ) -> Dict[str, SensorReading]:
        self._check_connected()
        pid_list = list(pids) if pids is not None else list(DIAGNOSTIC_PIDS)
        if dedupe:
            seen = set()
            pid_list = [p for p in pid_list if not (p in seen or seen.add(p))]

        results: Dict[str, SensorReading] = {}
        for pid in pid_list:
            try:
                result = self.scanner.read_pid(pid)
                if result.value is None:
                    continue
                value = result.value
                try:
                    value = round(float(value), round_to)
                except (TypeError, ValueError):
                    if stop_on_error:
                        raise
                    continue
                results[result.pid] = SensorReading(
                    name=result.name,
                    value=value,
                    unit=result.unit,
                    pid=result.pid,
                    raw_hex=result.raw_hex,
                    timestamp=cr_now(),
                    ecu=None,
                )
            except Exception as exc:
                if stop_on_error:
                    raise ScannerError(str(exc)) from exc
                continue
        return results
