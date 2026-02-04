from __future__ import annotations

from typing import Any, Dict

from app.application.scans import get_vehicle_info, read_dtcs, read_readiness, read_live_data


def collect_scan_report(scanner) -> Dict[str, Any]:
    info = get_vehicle_info(scanner)
    dtcs = read_dtcs(scanner)
    readiness = read_readiness(scanner)
    readings = read_live_data(scanner)

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
