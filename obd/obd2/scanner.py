from __future__ import annotations

from typing import Optional, Callable, List

from .base import BaseScanner
from .dtcs import DtcMixin
from ..pids.pid_mixin import PidMixin
from .readiness import ReadinessMixin
from .vehicle_info import VehicleInfoMixin
from .self_test import SelfTestMixin

from ..dtc import DTCDatabase


class OBDScanner(
    BaseScanner,
    PidMixin,
    DtcMixin,
    ReadinessMixin,
    VehicleInfoMixin,
    SelfTestMixin,
):
    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = 38400,
        manufacturer: Optional[str] = None,
        raw_logger: Optional[Callable[[str, str, List[str]], None]] = None,
    ):
        super().__init__(port=port, baudrate=baudrate, raw_logger=raw_logger)
        self.dtc_db = DTCDatabase(manufacturer=manufacturer)

    def set_manufacturer(self, manufacturer: str):
        self.dtc_db.set_manufacturer(manufacturer)


# Backwards/forwards compatible aliases
OBD2Scanner = OBDScanner
