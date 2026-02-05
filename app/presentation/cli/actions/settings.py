from __future__ import annotations

from pathlib import Path

from app.presentation.cli.actions.connect import disconnect_vehicle
from app.presentation.cli.i18n import t, get_available_languages, get_language, get_language_name, set_language
from app.bootstrap import get_container
from app.presentation.cli.actions.vehicle import select_brand, save_profile_for_group
from app.application.state import AppState
from app.presentation.cli.ui import clear_screen, press_enter, print_menu, print_header
from app.presentation.cli.actions.paywall import paywall_menu


def settings_menu(state: AppState) -> None:
    while True:
        clear_screen()
        print_menu(
            t("settings_header"),
            [
                ("1", f"{t('vehicle_make'):<20} [{state.brand_label or state.manufacturer.capitalize()}]"),
                ("2", f"{t('log_format'):<20} [{state.log_format.upper()}]"),
                ("3", f"{t('monitor_interval'):<20} [{state.monitor_interval}s]"),
                ("4", f"{t('verbose_logging'):<20} [{t('on') if state.verbose else t('off')}]"),
                ("5", t("view_ports")),
                ("6", t("view_bluetooth_ports")),
                ("7", f"{t('language'):<20} [{get_language_name(get_language())}]"),
                ("8", t("paywall_settings")),
                ("9", t("disconnect_now")),
                ("10", t("full_scan_reports")),
                ("0", t("back")),
            ],
        )

        choice = input(f"\n  {t('select_option')}: ").strip()
        if choice == "1":
            select_brand()
            dtc_db = state.ensure_dtc_db()
            print(f"\n  ✅ {t('set_to', value=state.brand_label or state.manufacturer.capitalize())}")
            print(f"     {t('loaded_codes', count=dtc_db.count)}")
            if dtc_db.loaded_files:
                print(f"     📁 Files: {', '.join(dtc_db.loaded_files)}")
            if state.vehicle_group != "generic":
                prompt_vehicle_profile_manual(state)
            save_profile_for_group()
            get_container().settings.save()
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
            get_container().settings.save()
            press_enter()
        elif choice == "3":
            print(f"\n  {t('current_interval', value=state.monitor_interval)}")
            new_interval = input(f"  {t('new_interval')}: ").strip()
            try:
                val = float(new_interval)
                if 0.5 <= val <= 10:
                    state.monitor_interval = val
                    print(f"\n  ✅ {t('interval_set', value=state.monitor_interval)}")
                    get_container().settings.save()
                else:
                    print(f"\n  ❌ {t('invalid_range')}")
            except ValueError:
                print(f"\n  ❌ {t('invalid_number')}")
            press_enter()
        elif choice == "4":
            state.set_verbose(not state.verbose)
            status = t("on") if state.verbose else t("off")
            print(f"\n  ✅ {t('set_to', value=status)}")
            if state.verbose:
                print(f"     {t('raw_log_file')}: {get_container().data_paths.raw_log_path()}")
            get_container().settings.save()
            press_enter()
        elif choice == "5":
            print(f"\n  📡 {t('available_ports')}:\n")
            ports = get_container().connection.scan_usb_ports()
            if ports:
                for port in ports:
                    print(f"    {port}")
            else:
                print(f"    {t('no_ports')}")
            press_enter()
        elif choice == "6":
            print(f"\n  🔵 {t('available_bluetooth_ports')}:\n")
            devices, _ = get_container().connection.scan_ble_devices(include_all=True)
            if devices:
                for port, name, rssi in devices:
                    label = f"{name} ({rssi} dBm)" if isinstance(rssi, int) else name
                    print(f"    {label} [{port}]")
            else:
                print(f"    {t('no_ports')}")
            print(f"\n  {t('veepeak_ble_hint')}")
            press_enter()
        elif choice == "7":
            languages = list(get_available_languages().items())
            print_menu(
                t("language_header"),
                [(str(idx + 1), name) for idx, (_, name) in enumerate(languages)],
            )
            lang_choice = input(f"\n  {t('select_option')} (1-{len(languages)}): ").strip()
            if lang_choice.isdigit():
                idx = int(lang_choice) - 1
                if 0 <= idx < len(languages):
                    code = languages[idx][0]
                    if set_language(code):
                        state.language = code
                        print(f"\n  ✅ {t('set_to', value=get_language_name(code))}")
                        print(f"\n  {t('profile_continue_prompt')}")
                        get_container().settings.save()
                    else:
                        print(f"\n  ❌ {t('invalid_number')}")
                else:
                    print(f"\n  ❌ {t('invalid_number')}")
            else:
                print(f"\n  ❌ {t('invalid_number')}")
            press_enter()
        elif choice == "8":
            paywall_menu()
        elif choice == "9":
            disconnect_vehicle(state)
            press_enter()
        elif choice == "10":
            show_full_scan_reports()
            press_enter()
        elif choice == "0":
            break


def show_full_scan_reports() -> None:
    print_header(t("full_scan_reports"))
    reports = [Path(path) for path in get_container().full_scan_reports.list()]
    if not reports:
        print(f"\n  {t('full_scan_report_none')}")
        return
    for idx, path in enumerate(reports, start=1):
        print(f"  {idx}. {path.name}")
    choice = input(f"\n  {t('full_scan_report_select')}: ").strip()
    if not choice.isdigit():
        return
    idx = int(choice) - 1
    if idx < 0 or idx >= len(reports):
        return
    print("\n" + "-" * 60)
    print(get_container().full_scan_reports.load(str(reports[idx])))


def prompt_vehicle_profile_manual(state: AppState) -> None:
    print(f"\n  {t('vin_manual_prompt')}")
    current = state.vehicle_profile or {}
    make_prompt = f"{t('vin_prompt_make')} [{current.get('make','')}]".rstrip()
    model_prompt = f"{t('vin_prompt_model')} [{current.get('model','')}]".rstrip()
    year_prompt = f"{t('vin_prompt_year')} [{current.get('year','')}]".rstrip()
    trim_prompt = f"{t('vin_prompt_trim')} [{current.get('trim','')}]".rstrip()

    make = input(f"  {make_prompt}: ").strip()
    model = input(f"  {model_prompt}: ").strip()
    year = input(f"  {year_prompt}: ").strip()
    trim = input(f"  {trim_prompt}: ").strip()

    result = get_container().vehicles.apply_manual_profile(make, model, year, trim)
    if not result:
        return
    profile, parsed = result
    if parsed:
        print(
            f"\n  Parsed: Make={profile.get('make') or '-'} | "
            f"Model={profile.get('model') or '-'} | "
            f"Year={profile.get('year') or '-'} | "
            f"Trim={profile.get('trim') or '-'}"
        )
    print(f"  ✅ {t('vehicle_specs_saved')}")
    input(f"\n  {t('press_enter')}")
