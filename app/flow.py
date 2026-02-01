from __future__ import annotations

from typing import List, Tuple

from obd.utils import VERSION, cr_timestamp

from app.actions.ai_report import ai_report_menu
from app.actions.clear_codes import clear_codes
from app.actions.connect import connect_vehicle, disconnect_vehicle
from app.actions.freeze_frame import read_freeze_frame
from app.actions.full_scan import run_full_scan
from app.actions.live_monitor import live_monitor
from app.actions.lookup import lookup_code
from app.actions.read_codes import read_codes
from app.actions.readiness import read_readiness
from app.actions.search import search_codes
from app.actions.settings import settings_menu
from app.actions.uds_tools import uds_tools_menu
from app.i18n import get_available_languages, set_language, t
from app.state import AppState
from app.ui import clear_screen, press_enter, print_header, print_menu, print_status


def run_cli(demo: bool = False) -> None:
    state = AppState(demo=demo)
    if demo:
        run_demo(state)
        return
    select_language(state)
    select_brand(state)
    main_menu(state)


def select_language(state: AppState) -> None:
    while True:
        clear_screen()
        print_menu(
            t("language_header"),
            [(code, name) for code, name in get_available_languages().items()],
        )
        choice = input(f"\n  {t('select_language')} (en/es): ").strip().lower()
        if set_language(choice):
            state.language = choice
            return


def select_brand(state: AppState) -> None:
    options: List[Tuple[str, str]] = [
        ("1", t("generic_all")),
        ("2", "Chrysler / Jeep / Dodge"),
        ("3", "Land Rover / Jaguar"),
    ]
    while True:
        clear_screen()
        print_menu(t("brand_header"), options)
        choice = input(f"\n  {t('select_brand')} (1-3): ").strip()
        if choice == "1":
            state.set_manufacturer("generic")
            return
        if choice == "2":
            state.set_manufacturer("chrysler")
            return
        if choice == "3":
            state.set_manufacturer("landrover")
            return


def main_menu(state: AppState) -> None:
    state.ensure_dtc_db()
    while True:
        clear_screen()
        print(f"\n  ╔════════════════════════════════════════════════════════╗")
        print(f"  ║           {t('app_name')} {VERSION:<23} ║")
        print(f"  ╚════════════════════════════════════════════════════════╝")
        print_status(state)
        print_menu(
            t("main_menu"),
            [
                ("1", t("connect")),
                ("2", t("disconnect")),
                ("3", t("full_scan")),
                ("4", t("read_codes")),
                ("5", t("live_monitor")),
                ("6", t("freeze_frame")),
                ("7", t("readiness")),
                ("8", t("clear_codes")),
                ("9", t("lookup")),
                ("10", t("search")),
                ("11", t("uds_tools")),
                ("12", t("ai_report")),
                ("S", t("settings")),
                ("0", t("exit")),
            ],
        )

        choice = input(f"\n  {t('select_option')}: ").strip().upper()
        if choice == "1":
            connect_vehicle(state)
            press_enter()
        elif choice == "2":
            disconnect_vehicle(state)
            press_enter()
        elif choice == "3":
            run_full_scan(state)
            press_enter()
        elif choice == "4":
            read_codes(state)
            press_enter()
        elif choice == "5":
            live_monitor(state)
            press_enter()
        elif choice == "6":
            read_freeze_frame(state)
            press_enter()
        elif choice == "7":
            read_readiness(state)
            press_enter()
        elif choice == "8":
            clear_codes(state)
            press_enter()
        elif choice == "9":
            lookup_code(state)
            press_enter()
        elif choice == "10":
            search_codes(state)
            press_enter()
        elif choice == "11":
            uds_tools_menu(state)
        elif choice == "12":
            ai_report_menu(state)
        elif choice == "S":
            settings_menu(state)
        elif choice == "0":
            if state.scanner and state.scanner.is_connected:
                state.scanner.disconnect()
                print(f"\n  🔌 {t('disconnected_at', time=cr_timestamp())}")
            print(f"\n  👋 {t('goodbye')}\n")
            break


def run_demo(state: AppState) -> None:
    clear_screen()
    print_header(f"{t('app_name')} {VERSION} - {t('demo_mode')}")
    print(f"  {t('time')}: {cr_timestamp()}")
    print(f"\n  {t('demo_intro')}\n")

    dtc_db = state.ensure_dtc_db()
    print(f"  📚 {t('loaded_codes', count=dtc_db.count)}")
    if dtc_db.loaded_files:
        print(f"  📁 Files: {', '.join(dtc_db.loaded_files)}\n")

    print(f"  Example codes:\n")
    examples = ["P0118", "P0220", "P0120", "P1489", "P1684", "B1601", "U0100"]
    for code in examples:
        info = dtc_db.lookup(code)
        if info:
            print(f"    {code}: {info.description}")
        else:
            print(f"    {code}: (not found)")

    print("\n" + "-" * 60)
    print(f"\n  {t('demo_tip1')}")
    print(f"  {t('demo_tip2')}")
    print(f"  {t('demo_tip3')}")
    print(f"  {t('demo_tip4')}")
