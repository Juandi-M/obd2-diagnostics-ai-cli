from __future__ import annotations

from typing import Any, Dict

from obd import OBDScanner


def collect_scan_report(scanner: OBDScanner) -> Dict[str, Any]:
    info = scanner.get_vehicle_info()
    dtcs = scanner.read_dtcs()
    readiness = scanner.read_readiness()
    readings = scanner.read_live_data()

    report: Dict[str, Any] = {
        "vehicle_info": info,
        "dtcs": [
            {
                "code": dtc.code,
                "status": dtc.status,
                "description": dtc.description,
            }
            for dtc in (dtcs or [])
        ],
        "readiness": {
            name: {
                "available": status.available,
                "complete": status.complete,
                "status": status.status_str,
            }
            for name, status in (readiness or {}).items()
        },
        "live_data": {
            pid: {
                "name": reading.name,
                "value": reading.value,
                "unit": reading.unit,
            }
            for pid, reading in (readings or {}).items()
        },
    }
    return report
