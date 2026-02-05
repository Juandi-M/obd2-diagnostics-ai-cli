from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain.entities import ExternalServiceError
from app.domain.ports import AiReportPort, AiConfigPort, VinDecoderPort
from app.infrastructure.ai.ai_report import (
    decode_vin_with_ai,
    decode_vin_with_vpic,
    request_ai_report,
)
from app.infrastructure.ai.openai_client import OpenAIError, get_api_key, get_model


class AiReportAdapter(AiReportPort):
    def decode_vin(self, vin: str, manufacturer: str) -> Optional[Dict[str, Any]]:
        try:
            return decode_vin_with_ai(vin, manufacturer)
        except OpenAIError as exc:
            raise ExternalServiceError(str(exc)) from exc

    def request_report(self, report_input: Dict[str, Any], language: str) -> str:
        try:
            return request_ai_report(report_input, language)
        except OpenAIError as exc:
            raise ExternalServiceError(str(exc)) from exc


class VinDecoderAdapter(VinDecoderPort):
    def decode_vpic(self, vin: str, model_year: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return decode_vin_with_vpic(vin, model_year=model_year)


class AiConfigAdapter(AiConfigPort):
    def get_api_key(self) -> Optional[str]:
        return get_api_key()

    def get_model(self) -> str:
        return get_model()
