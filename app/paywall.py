from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.i18n import t
from app.state import AppState
from app.ui import press_enter, print_header, print_menu
from openai.paywall.stripe_client import StripeError, create_checkout_session


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CONFIG_PATH = DATA_DIR / "paywall.json"


def load_paywall_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_paywall_config(config: Dict[str, Any]) -> None:
    CONFIG_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def paywall_menu(state: AppState) -> None:
    del state
    config = load_paywall_config()
    price_id = config.get("price_id", "")
    success_url = config.get("success_url", "")
    cancel_url = config.get("cancel_url", "")
    while True:
        print_menu(
            t("paywall_menu"),
            [
                ("1", f"{t('paywall_price_id')}: {price_id or '-'}"),
                ("2", f"{t('paywall_success_url')}: {success_url or '-'}"),
                ("3", f"{t('paywall_cancel_url')}: {cancel_url or '-'}"),
                ("4", t("paywall_checkout")),
                ("0", t("back")),
            ],
        )
        choice = input(f"\n  {t('select_option')}: ").strip()
        if choice == "1":
            price_id = input(f"  {t('paywall_price_id')}: ").strip()
        elif choice == "2":
            success_url = input(f"  {t('paywall_success_url')}: ").strip()
        elif choice == "3":
            cancel_url = input(f"  {t('paywall_cancel_url')}: ").strip()
        elif choice == "4":
            _start_checkout(price_id, success_url, cancel_url)
            press_enter()
        elif choice == "0":
            break

        config = {
            "price_id": price_id,
            "success_url": success_url,
            "cancel_url": cancel_url,
        }
        save_paywall_config(config)


def _start_checkout(price_id: str, success_url: str, cancel_url: str) -> None:
    if not price_id or not success_url or not cancel_url:
        print(f"\n  ❌ {t('paywall_missing_config')}")
        return
    try:
        session = create_checkout_session(
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except StripeError as exc:
        print(f"\n  ❌ {t('paywall_error')}: {exc}")
        return
    url = session.get("url")
    if url:
        print(f"\n  {t('paywall_checkout_url')}: {url}")
        print(f"  {t('paywall_checkout_hint')}")
    else:
        print(f"\n  ❌ {t('paywall_error')}: {t('paywall_no_url')}")
