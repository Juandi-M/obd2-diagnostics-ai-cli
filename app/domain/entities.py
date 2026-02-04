from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class AppError(Exception):
    pass


class NotConnectedError(AppError):
    pass


class ConnectionLostError(AppError):
    pass


class ScannerError(AppError):
    pass


class KLineError(AppError):
    pass


class UdsError(AppError):
    pass


class PaymentRequiredError(AppError):
    pass


class PaywallConfigError(AppError):
    pass


class ExternalServiceError(AppError):
    pass


@dataclass
class VehicleProfile:
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[str] = None
    trim: Optional[str] = None
    vin: Optional[str] = None
    protocol: Optional[str] = None
    source: Optional[str] = None


@dataclass
class ScanData:
    vehicle_info: Dict[str, Any] = field(default_factory=dict)
    dtcs: List[Dict[str, Any]] = field(default_factory=list)
    readiness: Dict[str, Any] = field(default_factory=dict)
    live_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModuleEntry:
    tx_id: str
    rx_id: str
    module_type: Optional[str] = None
    responses: List[str] = field(default_factory=list)
    requires_security: bool = False
    fingerprint: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportMeta:
    report_id: str
    created_at: str
    status: str
    model: Optional[str] = None
    file_path: Optional[str] = None
