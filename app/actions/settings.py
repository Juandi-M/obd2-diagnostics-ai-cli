from __future__ import annotations

from obd import ELM327

from app.i18n import t, get_available_languages, get_language, get_language_name, set_language
from app.paywall import paywall_menu
from app.state import AppState
from app.ui import clear_screen, press_enter, print_menu


def settings_menu(state: AppState) -> None:
    while True:
        clear_screen()
        print_menu(
            t("settings_header"),
            [
                ("1", f"{t('vehicle_make'):<20} [{state.manufacturer.capitalize()}]"),
                ("2", f"{t('log_format'):<20} [{state.log_format.upper()}]"),
                ("3", f"{t('monitor_interval'):<20} [{state.monitor_interval}s]"),
                ("4", t("view_ports")),
                ("5", f"{t('language'):<20} [{get_language_name(get_language())}]"),
                ("6", t("paywall_settings")),
                ("0", t("back")),
            ],
        )

        choice = input(f"\n  {t('select_option')}: ").strip()
        if choice == "1":
            print(f"\n  {t('available_manufacturers')}:")
            print(f"    1. {t('generic_all')}")
            print("    2. Chrysler / Jeep / Dodge")
            print("    3. Land Rover / Jaguar")

            mfr_choice = input(f"\n  {t('select_manufacturer')} (1-3): ").strip()
            if mfr_choice == "1":
                state.set_manufacturer("generic")
            elif mfr_choice == "2":
                state.set_manufacturer("chrysler")
            elif mfr_choice == "3":
                state.set_manufacturer("landrover")
            else:
                press_enter()
                continue

            dtc_db = state.ensure_dtc_db()
            print(f"\n  ✅ {t('set_to', value=state.manufacturer.capitalize())}")
            print(f"     {t('loaded_codes', count=dtc_db.count)}")
            if dtc_db.loaded_files:
                print(f"     📁 Files: {', '.join(dtc_db.loaded_files)}")
            press_enter()
        elif choice == "2":
            print(f"\n  {t('log_formats')}:")
            print(f"    1. {t('csv_desc')}")
            print(f"    2. {t('json_desc')}")

            fmt_choice = input(f"\n  {t('select_option')} (1-2): ").strip()
            if fmt_choice == "1":
                state.log_format = "csv"
            elif fmt_choice == "2":
                state.log_format = "json"

            print(f"\n  ✅ {t('set_to', value=state.log_format.upper())}")
            press_enter()
        elif choice == "3":
            print(f"\n  {t('current_interval', value=state.monitor_interval)}")
            new_interval = input(f"  {t('new_interval')}: ").strip()
            try:
                val = float(new_interval)
                if 0.5 <= val <= 10:
                    state.monitor_interval = val
                    print(f"\n  ✅ {t('interval_set', value=state.monitor_interval)}")
                else:
                    print(f"\n  ❌ {t('invalid_range')}")
            except ValueError:
                print(f"\n  ❌ {t('invalid_number')}")
            press_enter()
        elif choice == "4":
            print(f"\n  📡 {t('available_ports')}:\n")
            ports = ELM327.find_ports()
            if ports:
                for port in ports:
                    print(f"    {port}")
            else:
                print(f"    {t('no_ports')}")
            press_enter()
        elif choice == "5":
            print(f"\n  {t('select_language')}:\n")
            for code, name in get_available_languages().items():
                current = " ←" if code == get_language() else ""
                print(f"    {code}: {name}{current}")

            lang_choice = input(f"\n  {t('select_option')} (en/es): ").strip().lower()
            if set_language(lang_choice):
                state.language = lang_choice
                print(f"\n  ✅ {t('set_to', value=get_language_name(lang_choice))}")
            else:
                print(f"\n  ❌ {t('invalid_number')}")
            press_enter()
        elif choice == "6":
            paywall_menu(state)
        elif choice == "0":
            break
