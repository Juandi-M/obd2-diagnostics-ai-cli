from __future__ import annotations

import unittest
from unittest import mock

from app.domain.entities import ExternalServiceError, PaymentRequiredError
from app.infrastructure.billing import paywall_adapter
from app.infrastructure.billing.paywall_client import PaywallError, PaymentRequired


class FakeClient:
    def __init__(self):
        self.is_configured = True
        self.api_base = "http://example"
        self.identity = type("Identity", (), {"subject_id": "subject"})()

    def get_balance(self):
        return {"paid_credits": 1, "free_remaining": 0}

    def pending_total(self):
        return 0

    def ensure_identity(self):
        return True

    def consume(self, action, cost=1):
        return {"ok": True}

    def checkout(self):
        return "http://checkout"

    def wait_for_balance(self, *, min_paid=1, timeout_seconds=120):
        return {"paid_credits": min_paid, "free_remaining": 0}


class InfraPaywallAdapterTests(unittest.TestCase):
    def test_consume_maps_payment_required(self) -> None:
        class Client(FakeClient):
            def consume(self, action, cost=1):
                raise PaymentRequired("need payment")

        with mock.patch.object(paywall_adapter, "PaywallClient", return_value=Client()):
            adapter = paywall_adapter.PaywallAdapter()
            with self.assertRaises(PaymentRequiredError):
                adapter.consume("action", cost=1)

    def test_consume_maps_external_error(self) -> None:
        class Client(FakeClient):
            def consume(self, action, cost=1):
                raise PaywallError("boom")

        with mock.patch.object(paywall_adapter, "PaywallClient", return_value=Client()):
            adapter = paywall_adapter.PaywallAdapter()
            with self.assertRaises(ExternalServiceError):
                adapter.consume("action", cost=1)

    def test_checkout_maps_external_error(self) -> None:
        class Client(FakeClient):
            def checkout(self):
                raise PaywallError("boom")

        with mock.patch.object(paywall_adapter, "PaywallClient", return_value=Client()):
            adapter = paywall_adapter.PaywallAdapter()
            with self.assertRaises(ExternalServiceError):
                adapter.checkout()

    def test_bypass_flag(self) -> None:
        with mock.patch.object(paywall_adapter, "PaywallClient", return_value=FakeClient()):
            with mock.patch.object(paywall_adapter, "is_bypass_enabled", return_value=True):
                adapter = paywall_adapter.PaywallAdapter()
                self.assertTrue(adapter.is_bypass_enabled())
