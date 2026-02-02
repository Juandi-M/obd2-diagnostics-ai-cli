from __future__ import annotations

from typing import Dict, List, Any


def get_vehicle_info(scanner) -> Dict[str, Any]:
    return scanner.get_vehicle_info()


def read_dtcs(scanner):
    return scanner.read_dtcs()


def read_readiness(scanner):
    return scanner.read_readiness()


def read_live_data(scanner, pids=None):
    if pids is None:
        return scanner.read_live_data()
    return scanner.read_live_data(pids)


def read_freeze_frame(scanner):
    return scanner.read_freeze_frame()


def clear_codes(scanner) -> bool:
    return scanner.clear_codes()
