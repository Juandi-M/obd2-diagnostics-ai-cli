from __future__ import annotations

import os
from typing import List, Tuple

from .i18n import t, get_language
from .state import AppState


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def press_enter() -> None:
    input(f"\n  {t('press_enter')}")


def print_header(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_subheader(title: str) -> None:
    print("\n" + "-" * 40)
    print(f"  {title}")
    print("-" * 40)


def print_menu(title: str, options: List[Tuple[str, str]]) -> None:
    print("\n" + "╔" + "═" * 58 + "╗")
    print(f"║  {title:<55} ║")
    print("╠" + "═" * 58 + "╣")
    for num, text in options:
        print(f"║  {num}. {text:<53} ║")
    print("╚" + "═" * 58 + "╝")


def print_status(state: AppState) -> None:
    connected = state.active_scanner() is not None
    protocol = "K-LINE" if state.legacy_scanner and state.legacy_scanner.is_connected else "OBD2"
    conn_status = f"🟢 {t('connected')}" if connected else f"🔴 {t('disconnected')}"
    mfr = state.manufacturer.capitalize()
    lang = get_language().upper()
    print(
        f"\n  {t('status')}: {conn_status} | {t('vehicle')}: {mfr} | "
        f"{t('format')}: {state.log_format.upper()} | {t('protocol')}: {protocol} | {lang}"
    )


def handle_disconnection(state: AppState) -> None:
    if state.legacy_scanner:
        state.clear_legacy_scanner()
    if state.scanner:
        state.scanner._connected = False
    print(f"\n  ❌ {t('error')}: {t('device_disconnected')}")
    print(f"  🔌 {t('not_connected')}")
