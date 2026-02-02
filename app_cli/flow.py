from __future__ import annotations

from obd.utils import VERSION, cr_timestamp

from app_cli.actions.ai_report import ai_report_menu
from app_cli.actions.settings import prompt_vehicle_profile_manual
from app_cli.actions.clear_codes import clear_codes
from app_cli.actions.freeze_frame import read_freeze_frame
from app_cli.actions.full_scan import run_full_scan
from app_cli.actions.live_monitor import live_monitor
from app_cli.actions.lookup import lookup_code
from app_cli.actions.read_codes import read_codes
from app_cli.actions.readiness import read_readiness
from app_cli.actions.search import search_codes
from app_cli.actions.settings import settings_menu
from app_cli.actions.uds_tools import uds_tools_menu
from app_cli.i18n import get_available_languages, set_language, t
from app_cli.state import AppState
from app_cli.ui import clear_screen, press_enter, print_header, print_menu, print_status
from app_cli.settings_store import apply_settings, load_settings, save_settings, settings_from_state
from app_cli.vehicle import select_brand, save_profile_for_group


def run_cli(demo: bool = False) -> None:
    state = AppState(demo=demo)
    settings = load_settings()
    apply_settings(state, settings)
    if demo:
        run_demo(state)
        return
    select_language(state)
    if not start_session():
        return
    while True:
        session_setup(state)
        from app_cli.actions.connect import connect_vehicle
        if connection_flow(state, connect_vehicle):
            main_menu(state)
            break
        retry = input(f"\n  {t('session_retry_prompt')} ").strip().lower()
        if retry not in {"y", "yes", "s", "si"}:
            break


def select_language(state: AppState) -> None:
    while True:
        clear_screen()
        languages = list(get_available_languages().items())
        print_menu(
            t("language_header"),
            [(str(idx + 1), name) for idx, (_, name) in enumerate(languages)],
        )
        choice = input(f"\n  {t('select_language')} (1-{len(languages)}): ").strip()
        if not choice.isdigit():
            continue
        idx = int(choice) - 1
        if 0 <= idx < len(languages):
            code = languages[idx][0]
            if set_language(code):
                state.language = code
                return


def start_session() -> bool:
    clear_screen()
    print_header(t("start_header"))
    choice = input(f"\n  {t('start_prompt')} ").strip().lower()
    return choice not in {"q", "quit", "exit", "0"}


def session_setup(state: AppState) -> None:
    select_brand(state)
    if _needs_vehicle_profile(state):
        prompt_vehicle_profile_manual(state)
        save_profile_for_group(state)
        save_settings(settings_from_state(state))
        show_profile_summary(state)
        return
    if _wants_edit_profile(state):
        prompt_vehicle_profile_manual(state)
        save_profile_for_group(state)
        save_settings(settings_from_state(state))
        show_profile_summary(state)
        return
    save_profile_for_group(state)
    save_settings(settings_from_state(state))


def connection_flow(state: AppState, connect_vehicle) -> bool:
    while True:
        method = select_connection_method()
        if method == "back":
            return False
        if method == "usb":
            connected = connect_vehicle(state, auto=True, mode="usb")
        elif method == "ble":
            connected = connect_vehicle(state, auto=True, mode="ble")
        else:
            connected = connect_vehicle(state, auto=True)
        if connected:
            return True
        action = input(f"\n  {t('connect_retry_prompt')} ").strip().lower()
        if action in {"r", "retry"}:
            continue
        if action in {"b", "back"}:
            continue
        return False


def select_connection_method() -> str:
    clear_screen()
    print_menu(
        t("connect_method_header"),
        [
            ("1", t("connect_usb")),
            ("2", t("connect_ble")),
            ("0", t("back")),
        ],
    )
    choice = input(f"\n  {t('select_option')}: ").strip()
    if choice == "1":
        return "usb"
    if choice == "2":
        return "ble"
    return "back"


def show_profile_summary(state: AppState) -> None:
    clear_screen()
    _print_profile(state)
    input(f"\n  {t('profile_continue_prompt')}")


def _print_profile(state: AppState) -> None:
    profile = state.vehicle_profile or {}
    print_header(t("profile_summary_header"))
    manufacturer_label = state.manufacturer.capitalize()
    make_value = profile.get("make") or t("not_available")
    if _normalize_label(make_value) != _normalize_label(manufacturer_label):
        print(f"  {t('profile_manufacturer')}: {manufacturer_label}")
    print(f"  {t('profile_make')}: {make_value}")
    print(f"  {t('profile_model')}: {profile.get('model') or t('not_available')}")
    print(f"  {t('profile_year')}: {profile.get('year') or t('not_available')}")
    print(f"  {t('profile_trim')}: {profile.get('trim') or t('not_available')}")


def _needs_vehicle_profile(state: AppState) -> bool:
    profile = state.vehicle_profile or {}
    required = ["make", "model", "year", "trim"]
    return any(not profile.get(field) for field in required)


def _wants_edit_profile(state: AppState) -> bool:
    profile = state.vehicle_profile or {}
    if not any(profile.get(field) for field in ["make", "model", "year", "trim"]):
        return False
    clear_screen()
    _print_profile(state)
    choice = input(f"\n  {t('profile_edit_prompt')} ").strip().lower()
    return choice in {"e", "edit", "editar"}


def _normalize_label(value: str) -> str:
    if not value:
        return ""
    return (
        value.replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .lower()
    )


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
                ("1", t("full_scan")),
                ("2", t("read_codes")),
                ("3", t("live_monitor")),
                ("4", t("freeze_frame")),
                ("5", t("readiness")),
                ("6", t("clear_codes")),
                ("7", t("lookup")),
                ("8", t("search")),
                ("9", t("uds_tools")),
                ("10", t("ai_report")),
                ("S", t("settings")),
                ("0", t("exit")),
            ],
        )

        choice = input(f"\n  {t('select_option')}: ").strip().upper()
        if choice == "1":
            run_full_scan(state)
            press_enter()
        elif choice == "2":
            read_codes(state)
            press_enter()
        elif choice == "3":
            live_monitor(state)
            press_enter()
        elif choice == "4":
            read_freeze_frame(state)
            press_enter()
        elif choice == "5":
            read_readiness(state)
            press_enter()
        elif choice == "6":
            clear_codes(state)
            press_enter()
        elif choice == "7":
            lookup_code(state)
            press_enter()
        elif choice == "8":
            search_codes(state)
            press_enter()
        elif choice == "9":
            uds_tools_menu(state)
        elif choice == "10":
            ai_report_menu(state)
        elif choice == "S":
            settings_menu(state)
        elif choice == "0":
            if state.active_scanner():
                state.disconnect_all()
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
