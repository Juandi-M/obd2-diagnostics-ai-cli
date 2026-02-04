from __future__ import annotations

import webbrowser

from app.bootstrap import get_container
from app.domain.entities import ExternalServiceError, PaymentRequiredError
from app.presentation.cli.i18n import t
from app.presentation.cli.ui import clear_screen, press_enter, print_header, print_menu


def paywall_menu() -> None:
    while True:
        clear_screen()
        paywall = get_container().paywall
        api_base = paywall.api_base() or "-"
        subject_id = _short_id(paywall.subject_id() or "") or "-"
        cached = paywall.cached_balance()
        pending = paywall.pending_total()
        cached_summary = "-"
        if cached:
            cached_summary = f"{cached[0]}/{cached[1]}"
        balance_label = (
            f"{t('paywall_balance')} ({t('paywall_cached')}: {cached_summary}, {t('paywall_pending')}: {pending})"
        )
        print_menu(
            t("paywall_menu"),
            [
                ("1", f"{t('paywall_api_base')}: {api_base}"),
                ("2", f"{t('paywall_subject_id')}: {subject_id}"),
                ("3", balance_label),
                ("4", t("paywall_checkout")),
                ("5", t("paywall_reset_identity")),
                ("0", t("back")),
            ],
        )
        choice = input(f"\n  {t('select_option')}: ").strip()
        if choice == "1":
            _configure_api_base()
        elif choice == "2":
            _ensure_identity()
        elif choice == "3":
            _show_balance()
        elif choice == "4":
            _start_checkout()
        elif choice == "5":
            paywall.reset_identity()
            print(f"\n  {t('paywall_reset_done')}")
            press_enter()
        elif choice == "0":
            break


def _configure_api_base() -> None:
    print_header(t("paywall_api_base"))
    current = get_container().paywall.api_base() or "-"
    print(f"  {t('paywall_current')}: {current}")
    api_base = input(f"\n  {t('paywall_api_base_prompt')}: ").strip()
    if api_base:
        get_container().paywall.set_api_base(api_base)
        print(f"\n  {t('paywall_api_base_set')}")
    else:
        print(f"\n  {t('invalid_number')}")
    press_enter()


def _ensure_identity() -> None:
    paywall = get_container().paywall
    if not paywall.is_configured():
        print(f"\n  {t('paywall_not_configured')}")
        press_enter()
        return
    try:
        paywall.ensure_identity()
        identity = paywall.subject_id()
        print(f"\n  {t('paywall_identity_ready')}")
        print(f"  {t('paywall_subject_id')}: {identity}")
    except ExternalServiceError as exc:
        print(f"\n  {t('paywall_identity_failed')}: {exc}")
    press_enter()


def _show_balance() -> None:
    paywall = get_container().paywall
    if not paywall.is_configured():
        print(f"\n  {t('paywall_not_configured')}")
        cached = paywall.cached_balance()
        pending = paywall.pending_total()
        if cached:
            print(f"  {t('paywall_cached')}: {cached[0]} / {cached[1]}")
        print(f"  {t('paywall_pending')}: {pending}")
        press_enter()
        return
    try:
        cached_before = paywall.cached_balance()
        pending_before = paywall.pending_total()
        balance = paywall.get_balance()
        print(f"\n  {t('paywall_balance')}: ")
        print(f"    {t('paywall_free_remaining')}: {balance.free_remaining}")
        print(f"    {t('paywall_paid_credits')}: {balance.paid_credits}")
        print(f"    {t('paywall_pending')}: {paywall.pending_total()}")
        if cached_before:
            cached_total = cached_before[0] + cached_before[1]
            expected_total = cached_total + pending_before
            server_total = balance.free_remaining + balance.paid_credits
            if server_total != expected_total:
                print(f"\n  {t('paywall_discrepancy')}")
    except ExternalServiceError as exc:
        print(f"\n  {t('paywall_error')}: {exc}")
    press_enter()


def _start_checkout() -> None:
    paywall = get_container().paywall
    if not paywall.is_configured():
        print(f"\n  {t('paywall_not_configured')}")
        press_enter()
        return
    try:
        url = paywall.checkout()
        print(f"\n  {t('paywall_checkout_url')}: {url}")
        print(f"  {t('paywall_checkout_hint')}")
        webbrowser.open(url)
    except PaymentRequiredError as exc:
        print(f"\n  {t('paywall_payment_required')}: {exc}")
    except ExternalServiceError as exc:
        print(f"\n  {t('paywall_error')}: {exc}")
    press_enter()


def _short_id(value: str) -> str:
    if len(value) <= 8:
        return value
    return f"{value[:4]}...{value[-4:]}"
