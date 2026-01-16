#!/usr/bin/env python3
"""
OBD-II Scanner
==============
Open source vehicle diagnostic tool with interactive menu.
Multi-language support: English, Spanish, French, German, Portuguese, Italian

Usage:
    python3 obd_scan.py              # Interactive mode (recommended)
    python3 obd_scan.py --demo       # Demo mode without hardware
"""

import signal
import sys
import os
import time
from typing import Optional, Dict, List

from obd import OBDScanner, DTCDatabase, ELM327
from obd.logger import SessionLogger
from obd.utils import cr_timestamp, cr_time_only, VERSION, APP_NAME, cr_now
from obd.lang import t, set_language, get_language, get_available_languages, get_language_name

# Global state
_stop_monitoring = False
_scanner: Optional[OBDScanner] = None
_dtc_db: Optional[DTCDatabase] = None
_current_manufacturer: str = "generic"
_log_format: str = "csv"
_monitor_interval: float = 1.0


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global _stop_monitoring
    _stop_monitoring = True
    print("\n\n⏹️  " + t("cancelled"))


def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def press_enter():
    """Wait for user to press Enter."""
    input(f"\n  {t('press_enter')}")


# =============================================================================
# Display Helpers
# =============================================================================

def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_subheader(title: str):
    print("\n" + "-" * 40)
    print(f"  {title}")
    print("-" * 40)


def print_menu(title: str, options: List[tuple]):
    """Print a menu with numbered options."""
    print("\n" + "╔" + "═" * 58 + "╗")
    print(f"║  {title:<55} ║")
    print("╠" + "═" * 58 + "╣")
    
    for num, text in options:
        print(f"║  {num}. {text:<53} ║")
    
    print("╚" + "═" * 58 + "╝")


def print_status():
    """Print current connection status."""
    global _scanner, _current_manufacturer
    
    connected = _scanner and _scanner.is_connected
    conn_status = f"🟢 {t('connected')}" if connected else f"🔴 {t('disconnected')}"
    mfr = _current_manufacturer.capitalize()
    lang = get_language().upper()
    
    print(f"\n  {t('status')}: {conn_status} | {t('vehicle')}: {mfr} | {t('format')}: {_log_format.upper()} | {lang}")


# =============================================================================
# Menu Actions
# =============================================================================

def action_connect():
    """Connect to vehicle."""
    global _scanner
    
    print_header(t("connect_header"))
    print(f"  {t('time')}: {cr_timestamp()}")
    
    if _scanner and _scanner.is_connected:
        print(f"\n  ⚠️  {t('already_connected')}")
        confirm = input(f"  {t('disconnect_reconnect')} (y/n): ").strip().lower()
        if confirm not in ['y', 's', 'o', 'j']:  # yes/sí/oui/ja
            return
        _scanner.disconnect()
    
    # Initialize scanner if needed
    if not _scanner:
        _scanner = OBDScanner()
    
    print(f"\n🔍 {t('searching_adapter')}")
    
    ports = ELM327.find_ports()
    if not ports:
        print(f"\n  ❌ {t('no_ports_found')}")
        print(f"  💡 {t('adapter_tip')}")
        return
    
    print(f"  {t('found_ports', count=len(ports))}")
    
    for port in ports:
        try:
            print(f"\n  {t('trying_port', port=port)}")
            _scanner.elm.port = port
            _scanner.connect()
            print(f"  ✅ {t('connected_on', port=port)}")
            
            # Show vehicle info
            info = _scanner.get_vehicle_info()
            print(f"\n  {t('elm_version')}: {info.get('elm_version', 'unknown')}")
            print(f"  {t('protocol')}: {info.get('protocol', 'unknown')}")
            mil_status = f"🔴 {t('on')}" if info.get('mil_on') == 'Yes' else f"🟢 {t('off')}"
            print(f"  {t('mil_status')}: {mil_status}")
            print(f"  {t('dtc_count')}: {info.get('dtc_count', '?')}")
            return
            
        except Exception as e:
            print(f"  ❌ {t('connection_failed', error=str(e))}")
            try:
                _scanner.disconnect()
            except:
                pass
    
    print(f"\n  ❌ {t('no_vehicle_response')}")
    print(f"  💡 Tips:")
    print(f"     - Turn ignition to ON")
    print(f"     - Check OBD port connection")
    print(f"     - Try with engine running")


def action_disconnect():
    """Disconnect from vehicle."""
    global _scanner
    
    if not _scanner or not _scanner.is_connected:
        print(f"\n  ⚠️  {t('disconnected')}")
        return
    
    _scanner.disconnect()
    print(f"\n  🔌 {t('disconnected_at', time=cr_timestamp())}")


def action_full_scan():
    """Run full diagnostic scan."""
    global _scanner, _dtc_db
    
    if not _scanner or not _scanner.is_connected:
        print(f"\n  ❌ {t('not_connected')}")
        return
    
    print_header(t("scan_header"))
    print(f"  🕐 {t('report_time')}: {cr_timestamp()}")
    
    # Vehicle info
    print_subheader(t("vehicle_connection"))
    info = _scanner.get_vehicle_info()
    print(f"  {t('elm_version')}: {info.get('elm_version', 'unknown')}")
    print(f"  {t('protocol')}: {info.get('protocol', 'unknown')}")
    print(f"  {t('mil_status')}: {info.get('mil_on', 'unknown')}")
    print(f"  {t('dtc_count')}: {info.get('dtc_count', 'unknown')}")
    
    # DTCs
    print_subheader(t("dtc_header"))
    dtcs = _scanner.read_dtcs()
    
    if dtcs:
        for dtc in dtcs:
            emoji = "🚨" if dtc.status == "stored" else "⚠️"
            status = f" ({dtc.status})" if dtc.status != "stored" else ""
            print(f"\n  {emoji} {dtc.code}{status}")
            print(f"     └─ {dtc.description}")
    else:
        print(f"\n  ✅ {t('no_codes')}")
    
    # Readiness
    print_subheader(t("readiness_header"))
    readiness = _scanner.read_readiness()
    
    if readiness:
        complete = incomplete = 0
        for name, status in readiness.items():
            if name == "MIL (Check Engine Light)":
                continue
            if not status.available:
                emoji = "➖"
            elif status.complete:
                emoji = "✅"
                complete += 1
            else:
                emoji = "❌"
                incomplete += 1
            print(f"  {emoji} {name}: {status.status_str}")
        print(f"\n  {t('summary')}: {complete} {t('complete')}, {incomplete} {t('incomplete')}")
    
    # Live data
    print_subheader(t("live_header"))
    readings = _scanner.read_live_data()
    
    if readings:
        for reading in readings.values():
            print(f"\n  📈 {reading.name}")
            print(f"     └─ {reading.value} {reading.unit}")
            
            # Warnings
            if reading.name == "Engine Coolant Temperature":
                if reading.value > 105:
                    print(f"     🔥 {t('warning_high_temp')}")
                elif reading.value < 70:
                    print(f"     ⚠️  {t('warning_low_temp')}")
            elif "Throttle" in reading.name and reading.value > 5:
                print(f"     ⚠️  {t('warning_throttle')}")
    
    print("\n" + "=" * 60)
    print(f"  {t('report_time')}: {cr_timestamp()}")
    print("=" * 60)


def action_read_codes():
    """Read DTCs only."""
    global _scanner
    
    if not _scanner or not _scanner.is_connected:
        print(f"\n  ❌ {t('not_connected')}")
        return
    
    print_header(t("dtc_header"))
    print(f"  {t('time')}: {cr_timestamp()}\n")
    
    dtcs = _scanner.read_dtcs()
    
    if dtcs:
        for dtc in dtcs:
            status = f" [{dtc.status}]" if dtc.status != "stored" else ""
            print(f"  {dtc.code}{status}: {dtc.description}")
    else:
        print(f"  ✅ {t('no_codes')}")


def action_live_monitor():
    """Continuous live monitoring."""
    global _scanner, _stop_monitoring, _monitor_interval, _log_format
    
    if not _scanner or not _scanner.is_connected:
        print(f"\n  ❌ {t('not_connected')}")
        return
    
    _stop_monitoring = False
    signal.signal(signal.SIGINT, signal_handler)
    
    # Ask about logging
    print(f"\n  📊 {t('live_telemetry')}")
    log_choice = input(f"  {t('save_log_prompt')} (y/n): ").strip().lower()
    
    logger = None
    if log_choice in ['y', 's', 'o', 'j']:
        logger = SessionLogger("logs")
        log_file = logger.start_session(format=_log_format)
        print(f"  📝 {t('logging_to')}: {log_file}")
    
    print_header(t("live_telemetry"))
    print(f"  {t('started')}: {cr_timestamp()}")
    print(f"  {t('refresh')}: {_monitor_interval}s")
    print(f"\n  {t('press_ctrl_c')}\n")
    print("-" * 70)
    
    # Headers
    print(f"{t('time'):<10} {t('coolant'):<10} {'RPM':<8} {t('speed'):<8} {t('throttle'):<10} {t('pedal'):<8} {t('volts'):<8}")
    print("-" * 70)
    
    pids = ["05", "0C", "0D", "11", "49", "42"]
    
    while not _stop_monitoring:
        try:
            readings = _scanner.read_live_data(pids)
            
            if logger:
                logger.log_readings(readings)
            
            # Extract values
            coolant = readings.get("05")
            rpm = readings.get("0C")
            speed = readings.get("0D")
            throttle = readings.get("11")
            pedal = readings.get("49")
            volts = readings.get("42")
            
            time_str = cr_time_only()
            coolant_str = f"{coolant.value:.0f}°C" if coolant else "---"
            rpm_str = f"{rpm.value:.0f}" if rpm else "---"
            speed_str = f"{speed.value:.0f}km/h" if speed else "---"
            throttle_str = f"{throttle.value:.1f}%" if throttle else "---"
            pedal_str = f"{pedal.value:.1f}%" if pedal else "---"
            volts_str = f"{volts.value:.1f}V" if volts else "---"
            
            print(f"{time_str:<10} {coolant_str:<10} {rpm_str:<8} {speed_str:<8} {throttle_str:<10} {pedal_str:<8} {volts_str:<8}")
            
            time.sleep(_monitor_interval)
            
        except Exception as e:
            print(f"\n  ❌ {t('error')}: {e}")
            break
    
    print("-" * 70)
    
    if logger:
        summary = logger.end_session()
        print(f"\n📊 {t('session_summary')}:")
        print(f"   {t('file')}: {summary.get('file', 'N/A')}")
        print(f"   {t('duration')}: {summary.get('duration_seconds', 0):.1f} {t('seconds')}")
        print(f"   {t('readings')}: {summary.get('reading_count', 0)}")


def action_freeze_frame():
    """Read freeze frame data."""
    global _scanner
    
    if not _scanner or not _scanner.is_connected:
        print(f"\n  ❌ {t('not_connected')}")
        return
    
    print_header(t("freeze_header"))
    print(f"  {t('time')}: {cr_timestamp()}\n")
    
    freeze = _scanner.read_freeze_frame()
    
    if freeze:
        print(f"  {t('dtc_triggered')}: {freeze.dtc_code}\n")
        for reading in freeze.readings.values():
            print(f"  {reading.name}: {reading.value} {reading.unit}")
    else:
        print(f"  {t('no_freeze_data')}")
        print(f"  {t('freeze_tip')}")


def action_readiness():
    """Check readiness monitors."""
    global _scanner
    
    if not _scanner or not _scanner.is_connected:
        print(f"\n  ❌ {t('not_connected')}")
        return
    
    print_header(t("readiness_header"))
    print(f"  {t('time')}: {cr_timestamp()}\n")
    
    readiness = _scanner.read_readiness()
    
    if not readiness:
        print(f"  ❌ {t('unable_read_readiness')}")
        return
    
    complete = incomplete = na = 0
    
    for name, status in readiness.items():
        if not status.available:
            emoji = "➖"
            na += 1
        elif status.complete:
            emoji = "✅"
            complete += 1
        else:
            emoji = "❌"
            incomplete += 1
        print(f"  {emoji} {name}: {status.status_str}")
    
    print(f"\n  {t('summary')}:")
    print(f"    ✅ {t('complete')}: {complete}")
    print(f"    ❌ {t('incomplete')}: {incomplete}")
    print(f"    ➖ {t('not_available')}: {na}")
    
    if incomplete > 0:
        print(f"\n  💡 {t('readiness_tip')}")
        print(f"     {t('readiness_tip2')}")


def action_clear_codes():
    """Clear DTCs."""
    global _scanner
    
    if not _scanner or not _scanner.is_connected:
        print(f"\n  ❌ {t('not_connected')}")
        return
    
    print_header(t("clear_header"))
    print(f"\n  ⚠️  {t('clear_warning')}")
    print(f"     - {t('clear_warn1')}")
    print(f"     - {t('clear_warn2')}")
    print(f"     - {t('clear_warn3')}")
    print(f"     - {t('clear_warn4')}\n")
    
    confirm = input(f"  {t('type_yes')}: ").strip().upper()
    
    # Accept YES in multiple languages
    if confirm in ["YES", "SI", "SÍ", "OUI", "JA", "SIM"]:
        if _scanner.clear_dtcs():
            print(f"\n  ✅ {t('clear_success', time=cr_timestamp())}")
        else:
            print(f"\n  ❌ {t('clear_failed')}")
    else:
        print(f"\n  {t('cancelled')}")


def action_lookup_code():
    """Look up a specific DTC."""
    global _dtc_db
    
    if not _dtc_db:
        _dtc_db = DTCDatabase(manufacturer=_current_manufacturer if _current_manufacturer != "generic" else None)
    
    print_header(t("code_lookup_header"))
    print(f"  Database: {_dtc_db.count} {t('codes_loaded')}")
    print(f"  {t('manufacturer')}: {_current_manufacturer.capitalize()}\n")
    
    code = input(f"  {t('enter_code')}: ").strip().upper()
    
    if not code:
        return
    
    info = _dtc_db.lookup(code)
    
    if info:
        print(f"\n  📋 {info.code}")
        print(f"     └─ {info.description}")
        print(f"     └─ {t('source')}: {info.source}")
    else:
        print(f"\n  ❌ {t('code_not_found', code=code)}")
        
        # Try search
        results = _dtc_db.search(code)
        if results:
            print(f"\n  {t('similar_codes')}:")
            for r in results[:5]:
                print(f"    {r.code}: {r.description}")


def action_search_codes():
    """Search DTC database."""
    global _dtc_db
    
    if not _dtc_db:
        _dtc_db = DTCDatabase(manufacturer=_current_manufacturer if _current_manufacturer != "generic" else None)
    
    print_header(t("search_header"))
    
    query = input(f"  {t('search_prompt')}: ").strip()
    
    if not query:
        return
    
    results = _dtc_db.search(query)
    
    if results:
        print(f"\n  {t('found_codes', count=len(results))}\n")
        for info in results[:20]:  # Limit to 20 results
            print(f"  {info.code}: {info.description}")
        if len(results) > 20:
            print(f"\n  ... +{len(results) - 20} more")
    else:
        print(f"\n  {t('no_codes_found', query=query)}")


# =============================================================================
# Settings Menu
# =============================================================================

def menu_settings():
    """Settings submenu."""
    global _current_manufacturer, _dtc_db, _log_format, _monitor_interval
    
    while True:
        clear_screen()
        print_menu(t("settings_header"), [
            ("1", f"{t('vehicle_make'):<20} [{_current_manufacturer.capitalize()}]"),
            ("2", f"{t('log_format'):<20} [{_log_format.upper()}]"),
            ("3", f"{t('monitor_interval'):<20} [{_monitor_interval}s]"),
            ("4", t("view_ports")),
            ("5", f"{t('language'):<20} [{get_language_name(get_language())}]"),
            ("0", t("back")),
        ])
        
        choice = input(f"\n  {t('select_option')}: ").strip()
        
        if choice == "1":
            print(f"\n  {t('available_manufacturers')}:")
            print(f"    1. {t('generic_all')}")
            print(f"    2. Chrysler / Jeep / Dodge")
            print(f"    3. Land Rover / Jaguar")
            
            mfr_choice = input(f"\n  {t('select_manufacturer')} (1-3): ").strip()
            
            if mfr_choice == "1":
                _current_manufacturer = "generic"
            elif mfr_choice == "2":
                _current_manufacturer = "chrysler"
            elif mfr_choice == "3":
                _current_manufacturer = "landrover"
            
            # Reload database
            _dtc_db = DTCDatabase(manufacturer=_current_manufacturer if _current_manufacturer != "generic" else None)
            print(f"\n  ✅ {t('set_to', value=_current_manufacturer.capitalize())}")
            print(f"     {t('loaded_codes', count=_dtc_db.count)}")
            press_enter()
        
        elif choice == "2":
            print(f"\n  {t('log_formats')}:")
            print(f"    1. {t('csv_desc')}")
            print(f"    2. {t('json_desc')}")
            
            fmt_choice = input(f"\n  {t('select_manufacturer')} (1-2): ").strip()
            
            if fmt_choice == "1":
                _log_format = "csv"
            elif fmt_choice == "2":
                _log_format = "json"
            
            print(f"\n  ✅ {t('set_to', value=_log_format.upper())}")
            press_enter()
        
        elif choice == "3":
            print(f"\n  {t('current_interval', value=_monitor_interval)}")
            new_interval = input(f"  {t('new_interval')}: ").strip()
            
            try:
                val = float(new_interval)
                if 0.5 <= val <= 10:
                    _monitor_interval = val
                    print(f"\n  ✅ {t('interval_set', value=_monitor_interval)}")
                else:
                    print(f"\n  ❌ {t('invalid_range')}")
            except ValueError:
                print(f"\n  ❌ {t('invalid_number')}")
            press_enter()
        
        elif choice == "4":
            print(f"\n  📡 {t('available_ports')}:\n")
            ports = ELM327.find_ports()
            if ports:
                for p in ports:
                    print(f"    {p}")
            else:
                print(f"    {t('no_ports')}")
            press_enter()
        
        elif choice == "5":
            print(f"\n  {t('language')}:\n")
            for code, name in get_available_languages().items():
                current = " ←" if code == get_language() else ""
                print(f"    {code}: {name}{current}")
            
            lang_choice = input(f"\n  {t('select_manufacturer')} (en/es/fr/de/pt/it): ").strip().lower()
            
            if set_language(lang_choice):
                print(f"\n  ✅ {t('set_to', value=get_language_name(lang_choice))}")
            else:
                print(f"\n  ❌ Invalid language code")
            press_enter()
        
        elif choice == "0":
            break


# =============================================================================
# Demo Mode
# =============================================================================

def run_demo():
    """Demo mode without hardware."""
    global _dtc_db
    
    clear_screen()
    print_header(f"{t('app_name')} {VERSION} - DEMO MODE")
    print(f"  {t('time')}: {cr_timestamp()}")
    print(f"\n  This demonstrates scanner features without hardware.\n")
    
    # Load database
    _dtc_db = DTCDatabase()
    print(f"  📚 {t('loaded_codes', count=_dtc_db.count)}\n")
    
    # Show some example codes
    print(f"  Example codes:\n")
    examples = ["P0118", "P0220", "P0120", "P1489", "P1684", "B1601", "U0100"]
    
    for code in examples:
        info = _dtc_db.lookup(code)
        if info:
            print(f"    {code}: {info.description}")
    
    print("\n" + "-" * 60)
    print(f"\n  To use with a real vehicle:")
    print(f"    1. Connect ELM327 adapter to vehicle OBD port")
    print(f"    2. Turn ignition ON (or start engine)")
    print(f"    3. Run: python3 obd_scan.py")
    print(f"    4. Select option 1 to connect")


# =============================================================================
# Main Menu
# =============================================================================

def main_menu():
    """Main interactive menu."""
    global _scanner, _dtc_db
    
    # Initialize database
    _dtc_db = DTCDatabase()
    
    while True:
        clear_screen()
        
        print(f"\n  ╔════════════════════════════════════════════════════════╗")
        print(f"  ║           {t('app_name')} {VERSION:<23} ║")
        print(f"  ╚════════════════════════════════════════════════════════╝")
        
        print_status()
        
        print_menu(t("main_menu"), [
            ("1", t("connect")),
            ("2", t("full_scan")),
            ("3", t("read_codes")),
            ("4", t("live_monitor")),
            ("5", t("freeze_frame")),
            ("6", t("readiness")),
            ("7", t("clear_codes")),
            ("8", t("lookup")),
            ("9", t("search")),
            ("S", t("settings")),
            ("0", t("exit")),
        ])
        
        choice = input(f"\n  {t('select_option')}: ").strip().upper()
        
        if choice == "1":
            action_connect()
            press_enter()
        elif choice == "2":
            action_full_scan()
            press_enter()
        elif choice == "3":
            action_read_codes()
            press_enter()
        elif choice == "4":
            action_live_monitor()
            press_enter()
        elif choice == "5":
            action_freeze_frame()
            press_enter()
        elif choice == "6":
            action_readiness()
            press_enter()
        elif choice == "7":
            action_clear_codes()
            press_enter()
        elif choice == "8":
            action_lookup_code()
            press_enter()
        elif choice == "9":
            action_search_codes()
            press_enter()
        elif choice == "S":
            menu_settings()
        elif choice == "0":
            if _scanner and _scanner.is_connected:
                _scanner.disconnect()
                print(f"\n  🔌 {t('disconnected_at', time=cr_timestamp())}")
            print(f"\n  👋 {t('goodbye')}\n")
            break


def main():
    """Entry point."""
    # Check for --demo flag
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        run_demo()
        return
    
    # Run interactive menu
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n\n  👋 {t('goodbye')}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
