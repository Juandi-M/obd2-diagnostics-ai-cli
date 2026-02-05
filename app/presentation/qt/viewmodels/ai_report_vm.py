from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from PySide6.QtCore import QObject

from app.application.use_cases.ai_report import (
    AiReportService,
    build_report_input,
    detect_report_language,
    extract_report_parts,
    prepare_vehicle_profile,
    update_report_status,
)
from app.application.use_cases.ai_config import AiConfigService
from app.application.use_cases.scans import ScanService
from app.application.use_cases.reports import ReportsService
from app.application.use_cases.pdf_paths import PdfPathService
from app.application.use_cases.document_paths import DocumentPathService
from app.application.use_cases.paywall import PaywallService
from app.domain.entities import PaymentRequiredError


class AiReportViewModel(QObject):
    def __init__(
        self,
        ai_reports: AiReportService,
        ai_config: AiConfigService,
        paywall: PaywallService,
        reports: ReportsService,
        pdf_paths: PdfPathService,
        document_paths: DocumentPathService,
        scans: ScanService,
    ) -> None:
        super().__init__()
        self.ai_reports = ai_reports
        self.ai_config = ai_config
        self.paywall = paywall
        self.reports = reports
        self.pdf_paths = pdf_paths
        self.document_paths = document_paths
        self.scans = scans

    def is_configured(self) -> bool:
        """True when AI report generation is usable (OPENAI_API_KEY present)."""
        return self.ai_config.is_configured()

    def get_model(self) -> str:
        return self.ai_config.get_model()

    def decode_vin_vpic(self, vin: str, model_year: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self.ai_reports.decode_vin_vpic(vin, model_year=model_year)

    def decode_vin_ai(self, vin: str, manufacturer: str) -> Optional[Dict[str, Any]]:
        return self.ai_reports.decode_vin_ai(vin, manufacturer)

    def prepare_vehicle_profile(self, scan_payload: Dict[str, Any], state) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        return prepare_vehicle_profile(scan_payload, state)

    def build_report_input(self, *args, **kwargs) -> Dict[str, Any]:
        return build_report_input(*args, **kwargs)

    def detect_report_language(self, customer_notes: str, default_language: str, *, mode: str = "cli") -> str:
        return detect_report_language(customer_notes, default_language, mode=mode)

    def extract_report_parts(self, response: str, *, mode: str = "cli") -> Tuple[Optional[Dict[str, Any]], str]:
        return extract_report_parts(response, mode=mode)

    def update_report_status(
        self,
        report_path: str,
        *,
        status: str,
        response: Optional[str] = None,
        response_raw: Optional[str] = None,
        report_json: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None,
        model: Optional[str] = None,
        error: Optional[str] = None,
        vehicle_payload: Optional[Dict[str, Any]] = None,
        vehicle_profiles: Optional[Dict[str, Any]] = None,
    ) -> None:
        return update_report_status(
            self.reports,
            report_path,
            status=status,
            response=response,
            response_raw=response_raw,
            report_json=report_json,
            language=language,
            model=model,
            error=error,
            vehicle_payload=vehicle_payload,
            vehicle_profiles=vehicle_profiles,
        )

    def request_report(self, report_input: Dict[str, Any], language: str) -> str:
        return self.ai_reports.request_report(report_input, language)

    def export_pdf(
        self,
        payload: Dict[str, Any],
        output_path: str,
        *,
        report_json: Optional[Dict[str, Any]] = None,
        report_text: Optional[str] = None,
        language: Optional[str] = None,
    ) -> None:
        return self.ai_reports.export_pdf(
            payload,
            output_path,
            report_json=report_json,
            report_text=report_text,
            language=language,
        )

    def collect_scan_report(self) -> Dict[str, Any]:
        return self.scans.collect_scan_report()

    def save_report(self, payload: Dict[str, Any]) -> str:
        return self.reports.save_report(payload)

    def load_report(self, path: str) -> Dict[str, Any]:
        return self.reports.load_report(path)

    def write_report(self, path: str, payload: Dict[str, Any]) -> None:
        self.reports.write_report(path, payload)

    def document_pdf_path(self, vehicle_payload: Dict[str, Any]) -> str:
        return self.document_paths.ai_report_pdf_path(vehicle_payload)

    def report_pdf_path(self, report_id: str) -> str:
        return self.pdf_paths.report_pdf_path(report_id)

    # Paywall wrappers kept explicit to avoid confusion with AI config.
    def paywall_is_bypass_enabled(self) -> bool:
        return self.paywall.is_bypass_enabled()

    def paywall_api_base(self) -> Optional[str]:
        return self.paywall.api_base()

    def paywall_subject_id(self) -> Optional[str]:
        return self.paywall.subject_id()

    def paywall_is_configured(self) -> bool:
        return self.paywall.is_configured()

    def paywall_cached_balance(self):
        return self.paywall.cached_balance()

    def paywall_pending_total(self) -> int:
        return self.paywall.pending_total()

    def paywall_get_balance(self):
        return self.paywall.get_balance()

    def paywall_reset_identity(self) -> None:
        self.paywall.reset_identity()

    def paywall_checkout(self) -> str:
        return self.paywall.checkout()

    def paywall_consume(self, action: str, cost: int = 1) -> None:
        try:
            self.paywall.consume(action, cost=cost)
        except PaymentRequiredError:
            raise
