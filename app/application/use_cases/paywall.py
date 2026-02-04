from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.domain.entities import ExternalServiceError, PaymentRequiredError, PaywallConfigError
from app.domain.ports import PaywallPort


@dataclass
class PaywallDecision:
    ok: bool
    bypass: bool = False
    checkout_url: Optional[str] = None
    error: Optional[str] = None


class PaywallService:
    def __init__(self, port: PaywallPort) -> None:
        self.port = port

    def is_configured(self) -> bool:
        return self.port.is_configured()

    def is_bypass_enabled(self) -> bool:
        return self.port.is_bypass_enabled()

    def api_base(self) -> Optional[str]:
        return self.port.api_base()

    def set_api_base(self, api_base: str) -> None:
        self.port.set_api_base(api_base)

    def subject_id(self) -> Optional[str]:
        return self.port.subject_id()

    def cached_balance(self) -> Optional[tuple[int, int]]:
        return self.port.cached_balance()

    def ensure_credit(self, action: str, cost: int = 1) -> PaywallDecision:
        if self.port.is_bypass_enabled():
            return PaywallDecision(ok=True, bypass=True)
        if not self.port.is_configured():
            return PaywallDecision(ok=False, error=str(PaywallConfigError("Paywall not configured")))
        try:
            self.port.consume(action, cost=cost)
            return PaywallDecision(ok=True)
        except PaymentRequiredError:
            try:
                url = self.port.checkout()
            except ExternalServiceError as exc:
                return PaywallDecision(ok=False, error=str(exc))
            return PaywallDecision(ok=False, checkout_url=url)
        except ExternalServiceError as exc:
            return PaywallDecision(ok=False, error=str(exc))

    def wait_for_balance(self, *, min_paid: int = 1, timeout_seconds: int = 120):
        return self.port.wait_for_balance(min_paid=min_paid, timeout_seconds=timeout_seconds)

    def consume(self, action: str, cost: int = 1):
        return self.port.consume(action, cost=cost)

    def get_balance(self):
        return self.port.get_balance()

    def pending_total(self) -> int:
        return self.port.pending_total()

    def ensure_identity(self) -> Any:
        return self.port.ensure_identity()

    def reset_identity(self) -> None:
        self.port.reset_identity()

    def checkout(self) -> str:
        return self.port.checkout()
