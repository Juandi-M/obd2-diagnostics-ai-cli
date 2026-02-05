from __future__ import annotations

import unittest

from app.application.use_cases.paywall import PaywallService
from app.domain.entities import ExternalServiceError, PaymentRequiredError
from tests.app_fakes import DummyPaywall


class PaywallTests(unittest.TestCase):
    def test_bypass_enabled(self) -> None:
        service = PaywallService(DummyPaywall(bypass=True))
        decision = service.ensure_credit("action", cost=1)
        self.assertTrue(decision.ok)
        self.assertTrue(decision.bypass)

    def test_not_configured(self) -> None:
        service = PaywallService(DummyPaywall(configured=False))
        decision = service.ensure_credit("action", cost=1)
        self.assertFalse(decision.ok)
        self.assertIsNotNone(decision.error)

    def test_checkout_flow(self) -> None:
        service = PaywallService(DummyPaywall(consume_error=PaymentRequiredError("pay")))
        decision = service.ensure_credit("action", cost=1)
        self.assertFalse(decision.ok)
        self.assertIsNotNone(decision.checkout_url)

    def test_external_service_error(self) -> None:
        service = PaywallService(DummyPaywall(consume_error=ExternalServiceError("boom")))
        decision = service.ensure_credit("action", cost=1)
        self.assertFalse(decision.ok)
        self.assertIn("boom", decision.error or "")
