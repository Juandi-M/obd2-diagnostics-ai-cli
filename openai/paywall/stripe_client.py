from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


class StripeError(Exception):
    pass


def get_stripe_api_key() -> Optional[str]:
    return os.environ.get("STRIPE_API_KEY")


def create_checkout_session(
    *,
    price_id: str,
    success_url: str,
    cancel_url: str,
    customer_email: Optional[str] = None,
) -> Dict[str, Any]:
    api_key = get_stripe_api_key()
    if not api_key:
        raise StripeError("Missing STRIPE_API_KEY")

    payload = {
        "success_url": success_url,
        "cancel_url": cancel_url,
        "mode": "payment",
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": 1,
    }
    if customer_email:
        payload["customer_email"] = customer_email

    body = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except Exception as exc:
        raise StripeError(str(exc)) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StripeError("Invalid JSON response") from exc
