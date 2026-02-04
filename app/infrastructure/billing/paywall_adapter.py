from __future__ import annotations

from typing import Any, Optional

from app.domain.entities import ExternalServiceError, PaymentRequiredError
from app.domain.ports import PaywallPort
from app.infrastructure.billing.paywall_client import PaywallClient, PaywallError, PaymentRequired
from app.infrastructure.billing.paywall_config import (
    is_bypass_enabled,
    pending_total,
    reset_identity,
    load_balance,
    set_api_base,
)


class PaywallAdapter(PaywallPort):
    def __init__(self) -> None:
        self._client = PaywallClient()

    def is_configured(self) -> bool:
        return self._client.is_configured

    def is_bypass_enabled(self) -> bool:
        return is_bypass_enabled()

    def api_base(self) -> Optional[str]:
        return (self._client.api_base or "").strip() or None

    def set_api_base(self, api_base: str) -> None:
        set_api_base(api_base)
        self._client.api_base = (api_base or "").strip()

    def subject_id(self) -> Optional[str]:
        return self._client.identity.subject_id if self._client.identity else None

    def cached_balance(self) -> Optional[tuple[int, int]]:
        cached = load_balance()
        if cached:
            return cached[0], cached[1]
        return None

    def get_balance(self) -> Any:
        return self._client.get_balance()

    def pending_total(self) -> int:
        return pending_total()

    def ensure_identity(self) -> Any:
        return self._client.ensure_identity()

    def consume(self, action: str, cost: int = 1) -> Any:
        try:
            return self._client.consume(action, cost=cost)
        except PaymentRequired as exc:
            raise PaymentRequiredError(str(exc)) from exc
        except PaywallError as exc:
            raise ExternalServiceError(str(exc)) from exc

    def checkout(self) -> str:
        try:
            return self._client.checkout()
        except PaywallError as exc:
            raise ExternalServiceError(str(exc)) from exc

    def wait_for_balance(self, *, min_paid: int = 1, timeout_seconds: int = 120) -> Any:
        try:
            return self._client.wait_for_balance(min_paid=min_paid, timeout_seconds=timeout_seconds)
        except PaywallError as exc:
            raise ExternalServiceError(str(exc)) from exc

    def reset_identity(self) -> None:
        reset_identity()
