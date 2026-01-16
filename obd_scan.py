#!/usr/bin/env python3
"""
OBD-II Scanner
==============
Open source vehicle diagnostic tool with interactive menu.

Usage:
    python3 obd_scan.py              # Interactive mode (recommended)
    python3 obd_scan.py --demo       # Demo mode without hardware
"""

import signal
import sys
import os
from typing import Optional, Dict, List

from obd import OBDScanner, DTCDatabase, ELM327
from obd.logger import SessionLogger
from obd.utils import cr_timestamp, cr_time_only, VERSION, APP_NAME, cr_now, CR_TZ

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
    print("\n\n⏹️  Stopping...")


def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def press_enter():
    """Wait for user to press Enter."""
    input("\n  Press Enter to continue...")


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
    status = "🟢 Connected" if connected else "🔴 Disconnected"
    mfr = _current_manufacturer.capitalize()
    
    print(f"\n  Status: {status} | Vehicle: {mfr} | Format: {_log_format.upper()}")


# =============================================================================
# Menu Actions
# =============================================================================

def action_connect():
    """Connect to vehicle."""
    global _scanner
    
    print_header("CONNECT TO VEHICLE")
    print(f"  Time: {cr_timestamp()}")
    
    if _scanner and _scanner.is_connected:
        print("\n  ⚠️  Already connected!")
        confirm = input("  Disconnect and reconnect? (y/n): ").strip().lower()
        if confirm != 'y':
            return
        _scanner.disconnect()
    
    # Initialize scanner if needed
    if not _scanner:
        _scanner = OBDScanner()
    
    print("\n🔍 Searching for OBD adapter...")
    
    ports = ELM327.find_ports()
    if not ports:
        print("\n  ❌ No USB serial ports found!")
        print("  💡 Make sure your ELM327 is plugged in.")
        return
    
    print(f"  Found {len(ports)} port(s)")
    
    for port in ports:
        try:
            print(f"\n  Trying {port}...")
            _scanner.elm.port = port
            _scanner.connect()
            print(f"  ✅ Connected on {port}")
            
            # Show vehicle info
            info = _scanner.get_vehicle_info()
            print(f"\n  ELM327: {info.get('elm_version', 'unknown')}")
            print(f"  Protocol: {info.get('protocol', 'unknown')}")
            print(f"  Check Engine: {'🔴 ON' if info.get('mil_on') == 'Yes' else '🟢 OFF'}")
            print(f"  DTC Count: {info.get('dtc_count', '?')}")
            return
            
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            try:
                _scanner.disconnect()
            except:
                pass
    
    print("\n  ❌ Could not connect to any vehicle.")
    print("  💡 Tips:")
    print("     - Turn ignition to ON")
    print("     - Check OBD port connection")
    print("     - Try with engine running")


def action_disconnect():
    """Disconnect from vehicle."""
    global _scanner
    
    if not _scanner or not _scanner.is_connected:
        print("\n  ⚠️  Not connected.")
        return
    
    _scanner.disconnect()
    print(f"\n  🔌 Disconnected at {cr_timestamp()}")


def action_full_scan():
    """Run full diagnostic scan."""
    global _scanner, _dtc_db
    
    if not _scanner or not _scanner.is_connected:
        print("\n  ❌ Not connected! Connect first (option 1).")
        return
    
    print_header("FULL DIAGNOSTIC SCAN")
    print(f"  🕐 Time: {cr_timestamp()}")
    
    # Vehicle info
    print_subheader("VEHICLE CONNECTION")
    info = _scanner.get_vehicle_info()
    print(f"  ELM327: {info.get('elm_version', 'unknown')}")
    print(f"  Protocol: {info.get('protocol', 'unknown')}")
    print(f"  MIL (Check Engine): {info.get('mil_on', 'unknown')}")
    print(f"  DTC Count: {info.get('dtc_count', 'unknown')}")
    
    # DTCs
    print_subheader("DIAGNOSTIC TROUBLE CODES")
    dtcs = _scanner.read_dtcs()
    
    if dtcs:
        for dtc in dtcs:
            emoji = "🚨" if dtc.status == "stored" else "⚠️"
            status = f" ({dtc.status})" if dtc.status != "stored" else ""
            print(f"\n  {emoji} {dtc.code}{status}")
            print(f"     └─ {dtc.description}")
    else:
        print("\n  ✅ No trouble codes stored")
    
    # Readiness
    print_subheader("READINESS MONITORS")
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
        print(f"\n  Summary: {complete} complete, {incomplete} incomplete")
    
    # Live data
    print_subheader("LIVE SENSOR DATA")
    readings = _scanner.read_live_data()
    
    if readings:
        for reading in readings.values():
            print(f"\n  📈 {reading.name}")
            print(f"     └─ {reading.value} {reading.unit}")
            
            # Warnings
            if reading.name == "Engine Coolant Temperature":
                if reading.value > 105:
                    print("     🔥 HIGH - Possible overheating!")
                elif reading.value < 70:
                    print("     ⚠️  LOW - Not at operating temp")
            elif "Throttle" in reading.name and reading.value > 5:
                print("     ⚠️  Not fully closed at idle")
    
    print("\n" + "=" * 60)
    print(f"  Scan completed: {cr_timestamp()}")
    print("=" * 60)


def action_read_codes():
    """Read DTCs only."""
    global _scanner
    
    if not _scanner or not _scanner.is_connected:
        print("\n  ❌ Not connected! Connect first.")
        return
    
    print_header("DIAGNOSTIC TROUBLE CODES")
    print(f"  Time: {cr_timestamp()}\n")
    
    dtcs = _scanner.read_dtcs()
    
    if dtcs:
        for dtc in dtcs:
            status = f" [{dtc.status}]" if dtc.status != "stored" else ""
            print(f"  {dtc.code}{status}: {dtc.description}")
    else:
        print("  ✅ No trouble codes found.")


def action_live_monitor():
    """Continuous live monitoring."""
    global _scanner, _stop_monitoring, _monitor_interval, _log_format
    
    if not _scanner or not _scanner.is_connected:
        print("\n  ❌ Not connected! Connect first.")
        return
    
    _stop_monitoring = False
    signal.signal(signal.SIGINT, signal_handler)
    
    # Ask about logging
    print("\n  📊 Live Telemetry Monitor")
    log_choice = input("  Save to log file? (y/n): ").strip().lower()
    
    logger = None
    if log_choice == 'y':
        logger = SessionLogger("logs")
        log_file = logger.start_session(format=_log_format)
        print(f"  📝 Logging to: {log_file}")
    
    print_header("LIVE TELEMETRY")
    print(f"  Started: {cr_timestamp()}")
    print(f"  Refresh: {_monitor_interval}s")
    print(f"\n  Press Ctrl+C to stop\n")
    print("-" * 70)
    
    # Headers
    print(f"{'Time':<10} {'Coolant':<10} {'RPM':<8} {'Speed':<8} {'Throttle':<10} {'Pedal':<8} {'Volts':<8}")
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
            
            import time
            time.sleep(_monitor_interval)
            
        except Exception as e:
            print(f"\n  ❌ Error: {e}")
            break
    
    print("-" * 70)
    
    if logger:
        summary = logger.end_session()
        print(f"\n📊 Session Summary:")
        print(f"   File: {summary.get('file', 'N/A')}")
        print(f"   Duration: {summary.get('duration_seconds', 0):.1f} seconds")
        print(f"   Readings: {summary.get('reading_count', 0)}")


def action_freeze_frame():
    """Read freeze frame data."""
    global _scanner
    
    if not _scanner or not _scanner.is_connected:
        print("\n  ❌ Not connected! Connect first.")
        return
    
    print_header("FREEZE FRAME DATA")
    print(f"  Time: {cr_timestamp()}\n")
    
    freeze = _scanner.read_freeze_frame()
    
    if freeze:
        print(f"  DTC that triggered: {freeze.dtc_code}\n")
        for reading in freeze.readings.values():
            print(f"  {reading.name}: {reading.value} {reading.unit}")
    else:
        print("  No freeze frame data available.")
        print("  (Freeze frames are captured when a DTC is stored)")


def action_readiness():
    """Check readiness monitors."""
    global _scanner
    
    if not _scanner or not _scanner.is_connected:
        print("\n  ❌ Not connected! Connect first.")
        return
    
    print_header("READINESS MONITORS")
    print(f"  Time: {cr_timestamp()}\n")
    
    readiness = _scanner.read_readiness()
    
    if not readiness:
        print("  ❌ Unable to read readiness monitors.")
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
    
    print(f"\n  Summary:")
    print(f"    ✅ Complete: {complete}")
    print(f"    ❌ Incomplete: {incomplete}")
    print(f"    ➖ Not Available: {na}")
    
    if incomplete > 0:
        print("\n  💡 Incomplete monitors need drive cycles to complete.")
        print("     Normal after clearing codes or disconnecting battery.")


def action_clear_codes():
    """Clear DTCs."""
    global _scanner
    
    if not _scanner or not _scanner.is_connected:
        print("\n  ❌ Not connected! Connect first.")
        return
    
    print_header("CLEAR TROUBLE CODES")
    print(f"\n  ⚠️  WARNING: This will:")
    print("     - Clear all stored DTCs")
    print("     - Turn off Check Engine light")
    print("     - Reset ALL readiness monitors")
    print("     - Permanent codes will NOT be cleared\n")
    
    confirm = input("  Type 'YES' to confirm: ").strip()
    
    if confirm == "YES":
        if _scanner.clear_dtcs():
            print(f"\n  ✅ DTCs cleared at {cr_timestamp()}")
        else:
            print("\n  ❌ Failed to clear DTCs")
    else:
        print("\n  Cancelled.")


def action_lookup_code():
    """Look up a specific DTC."""
    global _dtc_db
    
    if not _dtc_db:
        _dtc_db = DTCDatabase(manufacturer=_current_manufacturer)
    
    print_header("CODE LOOKUP")
    print(f"  Database: {_dtc_db.count} codes loaded")
    print(f"  Manufacturer: {_current_manufacturer.capitalize()}\n")
    
    code = input("  Enter code (e.g., P0118): ").strip().upper()
    
    if not code:
        return
    
    info = _dtc_db.lookup(code)
    
    if info:
        print(f"\n  📋 {info.code}")
        print(f"     └─ {info.description}")
        print(f"     └─ Source: {info.source}")
    else:
        print(f"\n  ❌ Code '{code}' not found in database.")
        
        # Try search
        results = _dtc_db.search(code)
        if results:
            print(f"\n  Similar codes:")
            for r in results[:5]:
                print(f"    {r.code}: {r.description}")


def action_search_codes():
    """Search DTC database."""
    global _dtc_db
    
    if not _dtc_db:
        _dtc_db = DTCDatabase(manufacturer=_current_manufacturer)
    
    print_header("SEARCH CODES")
    
    query = input("  Search term (e.g., 'throttle', 'coolant'): ").strip()
    
    if not query:
        return
    
    results = _dtc_db.search(query)
    
    if results:
        print(f"\n  Found {len(results)} codes:\n")
        for info in results[:20]:  # Limit to 20 results
            print(f"  {info.code}: {info.description}")
        if len(results) > 20:
            print(f"\n  ... and {len(results) - 20} more.")
    else:
        print(f"\n  No codes found matching '{query}'")


# =============================================================================
# Settings Menu
# =============================================================================

def menu_settings():
    """Settings submenu."""
    global _current_manufacturer, _dtc_db, _log_format, _monitor_interval
    
    while True:
        clear_screen()
        print_menu("SETTINGS", [
            ("1", f"Vehicle Make      [{_current_manufacturer.capitalize()}]"),
            ("2", f"Log Format        [{_log_format.upper()}]"),
            ("3", f"Monitor Interval  [{_monitor_interval}s]"),
            ("4", "View Serial Ports"),
            ("0", "Back to Main Menu"),
        ])
        
        choice = input("\n  Select option: ").strip()
        
        if choice == "1":
            print("\n  Available manufacturers:")
            print("    1. Generic (all codes)")
            print("    2. Chrysler / Jeep / Dodge")
            print("    3. Land Rover / Jaguar")
            
            mfr_choice = input("\n  Select (1-3): ").strip()
            
            if mfr_choice == "1":
                _current_manufacturer = "generic"
            elif mfr_choice == "2":
                _current_manufacturer = "chrysler"
            elif mfr_choice == "3":
                _current_manufacturer = "landrover"
            
            # Reload database
            _dtc_db = DTCDatabase(manufacturer=_current_manufacturer if _current_manufacturer != "generic" else None)
            print(f"\n  ✅ Set to {_current_manufacturer.capitalize()}")
            print(f"     Loaded {_dtc_db.count} codes")
            press_enter()
        
        elif choice == "2":
            print("\n  Log formats:")
            print("    1. CSV (spreadsheet compatible)")
            print("    2. JSON (structured data)")
            
            fmt_choice = input("\n  Select (1-2): ").strip()
            
            if fmt_choice == "1":
                _log_format = "csv"
            elif fmt_choice == "2":
                _log_format = "json"
            
            print(f"\n  ✅ Log format set to {_log_format.upper()}")
            press_enter()
        
        elif choice == "3":
            print(f"\n  Current interval: {_monitor_interval} seconds")
            new_interval = input("  New interval (0.5 - 10): ").strip()
            
            try:
                val = float(new_interval)
                if 0.5 <= val <= 10:
                    _monitor_interval = val
                    print(f"\n  ✅ Interval set to {_monitor_interval}s")
                else:
                    print("\n  ❌ Must be between 0.5 and 10")
            except ValueError:
                print("\n  ❌ Invalid number")
            press_enter()
        
        elif choice == "4":
            print("\n  📡 Available serial ports:\n")
            ports = ELM327.find_ports()
            if ports:
                for p in ports:
                    print(f"    {p}")
            else:
                print("    No USB serial ports found")
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
    print_header(f"{APP_NAME} v{VERSION} - DEMO MODE")
    print(f"  Time: {cr_timestamp()}")
    print("\n  This demonstrates scanner features without hardware.\n")
    
    # Load database
    _dtc_db = DTCDatabase()
    print(f"  📚 Loaded {_dtc_db.count} DTC codes\n")
    
    # Show some example codes
    print("  Example codes your scanner can identify:\n")
    examples = ["P0118", "P0220", "P0120", "P1489", "P1684", "B1601", "U0100"]
    
    for code in examples:
        info = _dtc_db.lookup(code)
        if info:
            print(f"    {code}: {info.description}")
    
    print("\n" + "-" * 60)
    print("\n  To use with a real vehicle:")
    print("    1. Connect ELM327 adapter to vehicle OBD port")
    print("    2. Turn ignition ON (or start engine)")
    print("    3. Run: python3 obd_scan.py")
    print("    4. Select option 1 to connect")


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
        print(f"  ║           {APP_NAME} v{VERSION}                       ║")
        print(f"  ╚════════════════════════════════════════════════════════╝")
        
        print_status()
        
        print_menu("MAIN MENU", [
            ("1", "Connect to Vehicle"),
            ("2", "Full Diagnostic Scan"),
            ("3", "Read Trouble Codes"),
            ("4", "Live Telemetry Monitor"),
            ("5", "Freeze Frame Data"),
            ("6", "Readiness Monitors"),
            ("7", "Clear Codes"),
            ("8", "Lookup Code"),
            ("9", "Search Codes"),
            ("S", "Settings"),
            ("0", "Exit"),
        ])
        
        choice = input("\n  Select option: ").strip().upper()
        
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
                print(f"\n  🔌 Disconnected at {cr_timestamp()}")
            print("\n  👋 Goodbye!\n")
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
        print("\n\n  👋 Goodbye!\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
