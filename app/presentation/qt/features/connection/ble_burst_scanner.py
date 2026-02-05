from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.presentation.qt.features.connection.devices import DeviceEntry, looks_like_obd_adapter


@dataclass
class BleBurstScanner:
    """State machine for "burst" BLE scans.

    BleakScanner.discover() only yields results after the timeout finishes.
    We chain short scans and merge results so the UI updates every ~1s.
    """

    max_iters: int = 6
    timeout_s: float = 0.9

    running: bool = False
    include_all: bool = False
    iter: int = 0
    _seen: Dict[str, Tuple[str, int]] = field(default_factory=dict)

    def start(self, include_all: bool) -> None:
        self.running = True
        self.include_all = bool(include_all)
        self.iter = 0
        self._seen = {}

    def stop(self) -> None:
        self.running = False

    def next_iter(self) -> int:
        self.iter += 1
        return self.iter

    def merge(self, devices: List[DeviceEntry]) -> List[DeviceEntry]:
        for port, name, rssi in devices:
            try:
                rssi_i = int(rssi) if rssi is not None else -999
            except Exception:
                rssi_i = -999
            prev = self._seen.get(port)
            if prev is None or rssi_i > prev[1]:
                self._seen[port] = (str(name), rssi_i)
        return [(port, name, rssi) for port, (name, rssi) in self._seen.items()]

    def should_stop(self, devices: List[DeviceEntry]) -> bool:
        if not self.running:
            return True
        found_any = bool(devices)
        found_adapter = any(looks_like_obd_adapter(name) for _, name, _ in devices)
        if found_adapter:
            return True
        if found_any and not self.include_all and self.iter >= 2:
            # In filtered mode our BLE heuristics may include a couple of candidates;
            # run at least two short scans to improve hit rate before stopping.
            return True
        if self.iter >= self.max_iters:
            return True
        return False
