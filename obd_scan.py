#!/usr/bin/env python3
"""
Jeep OBD-II Scanner
===================
Open source vehicle diagnostic tool.

Usage:
    python3 jeep_scan.py --scan                  # Full diagnostic scan
    python3 jeep_scan.py --monitor               # Continuous telemetry (Ctrl+C to stop)
    python3 jeep_scan.py --monitor --log         # Monitor + save to CSV
    python3 jeep_scan.py --freeze                # Read freeze frame data
    python3 jeep_scan.py --readiness             # Check readiness monitors
    python3 jeep_scan.py --codes                 # Read DTCs only
    python3 jeep_scan.py --lookup P0118          # Look up a code
"""

import argparse
import signal
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List

from obd import OBDScanner, DTCDatabase, ELM327
from obd.logger import SessionLogger

# Costa Rica timezone
CR_TZ = timezone(timedelta(hours=-6))

# Global flag for stopping monitor mode
_stop_monitoring = False


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global _stop_monitoring
    _stop_monitoring = True
    print("\n\n⏹️  Stopping monitor...")


def cr_timestamp() -> str:
    """Return current Costa Rica time (UTC-6) formatted."""
    return datetime.now(CR_TZ).strftime("%Y-%m-%d %H:%M:%S")


def print_header(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_subheader(title: str) -> None:
    print("\n" + "-" * 40)
    print(f"  {title}")
    print("-" * 40)


# =============================================================================
# Command Handlers
# =============================================================================

def run_full_scan(scanner: OBDScanner):
    """Full diagnostic scan with DTCs, readiness, and live data."""
    print_header("JEEP PATRIOT DIAGNOSTIC REPORT")
    print(f"  🕐 Report Time: {cr_timestamp()}")

    # Vehicle info
    print_subheader("VEHICLE CONNECTION")
    info = scanner.get_vehicle_info()
    print(f"  ELM327 Version: {info.get('elm_version', 'unknown')}")
    print(f"  Protocol: {info.get('protocol', 'unknown')}")
    print(f"  MIL (Check Engine): {info.get('mil_on', 'unknown')}")
    print(f"  DTC Count: {info.get('dtc_count', 'unknown')}")

    # DTCs
    print_subheader("DIAGNOSTIC TROUBLE CODES")
    dtcs = scanner.read_dtcs()

    if dtcs:
        for dtc in dtcs:
            status_emoji = "🚨" if dtc.status == "stored" else "⚠️"
            status_text = f" ({dtc.status})" if dtc.status != "stored" else ""
            print(f"\n  {status_emoji} {dtc.code}{status_text}")
            print(f"     └─ {dtc.description}")
            print(f"     └─ Read at: {dtc.timestamp_str}")
    else:
        print("\n  ✅ No trouble codes stored")

    # Readiness monitors
    print_subheader("READINESS MONITORS")
    readiness = scanner.read_readiness()
    
    if readiness:
        complete_count = 0
        incomplete_count = 0
        
        for name, status in readiness.items():
            if name == "MIL (Check Engine Light)":
                continue  # Already shown above
            
            if not status.available:
                emoji = "➖"
            elif status.complete:
                emoji = "✅"
                complete_count += 1
            else:
                emoji = "❌"
                incomplete_count += 1
            
            print(f"  {emoji} {name}: {status.status_str}")
        
        print(f"\n  Summary: {complete_count} complete, {incomplete_count} incomplete")
    else:
        print("\n  ❌ Unable to read readiness monitors")

    # Live data
    print_subheader("LIVE SENSOR DATA")
    print(f"  Timestamp: {cr_timestamp()}")
    readings = scanner.read_live_data()

    if readings:
        for reading in readings.values():
            print(f"\n  📈 {reading.name}")
            print(f"     └─ {reading.value} {reading.unit}")

            if reading.name == "Engine Coolant Temperature":
                if reading.value < 70:
                    print("     ⚠️  LOW - Engine not at operating temp")
                elif reading.value > 105:
                    print("     🔥 HIGH - Possible overheating!")
            elif "Throttle" in reading.name and reading.value > 5:
                print("     ⚠️  Not fully closed at idle")
    else:
        print("\n  ❌ Unable to read sensor data")

    print("\n" + "=" * 60)
    print(f"  Report completed: {cr_timestamp()}")
    print("=" * 60)


def run_codes_only(scanner: OBDScanner) -> None:
    """Read and display DTCs only."""
    print(f"\n📋 Reading Diagnostic Trouble Codes...")
    print(f"   Timestamp: {cr_timestamp()}\n")
    
    dtcs = scanner.read_dtcs()

    if dtcs:
        for dtc in dtcs:
            status = f" [{dtc.status}]" if dtc.status != "stored" else ""
            print(f"{dtc.code}{status}: {dtc.description}")
    else:
        print("No trouble codes found.")


def run_live_data(scanner: OBDScanner, pids: Optional[List[str]] = None) -> None:
    """Single read of live sensor data."""
    print(f"\n📊 Reading Live Sensor Data...")
    print(f"   Timestamp: {cr_timestamp()}\n")
    
    readings = scanner.read_live_data(pids)

    if readings:
        for reading in readings.values():
            print(f"{reading.name}: {reading.value} {reading.unit}")
    else:
        print("No sensor data available.")


def run_monitor(scanner: OBDScanner, interval: float = 1.0, log: bool = False, log_format: str = "csv"):
    """
    Continuous live telemetry monitoring.
    Optionally logs to CSV/JSON file.
    """
    global _stop_monitoring
    _stop_monitoring = False

    signal.signal(signal.SIGINT, signal_handler)

    # Set up logger if requested
    logger: Optional[SessionLogger] = None
    if log:
        logger = SessionLogger("logs")
        log_file = logger.start_session(format=log_format)
        print(f"  📝 Logging to: {log_file}")

    print_header("LIVE TELEMETRY MONITOR")
    print(f"  Started: {cr_timestamp()}")
    print(f"  Refresh: {interval}s")
    if logger:
        print(f"  Log format: {log_format.upper()}")
    print(f"\n  Press Ctrl+C to stop\n")
    print("-" * 70)

    # Column headers
    print(f"{'Time':<10} {'Coolant':<10} {'RPM':<8} {'Speed':<8} {'Throttle':<10} {'Pedal':<8} {'Volts':<8}")
    print(f"{'─'*10} {'─'*10} {'─'*8} {'─'*8} {'─'*10} {'─'*8} {'─'*8}")

    monitor_pids = ["05", "0C", "0D", "11", "49", "42"]
    reading_count = 0

    while not _stop_monitoring:
        try:
            readings = scanner.read_live_data(monitor_pids)

            # Log if enabled
            if logger:
                logger.log_readings(readings)
                
                # Log warnings as events
                coolant = readings.get("05")
                if coolant and coolant.value > 105:
                    logger.log_event("WARNING", f"Coolant temp HIGH: {coolant.value}°C")

            # Extract values
            coolant = readings.get("05")
            rpm = readings.get("0C")
            speed = readings.get("0D")
            throttle = readings.get("11")
            pedal = readings.get("49")
            volts = readings.get("42")

            time_str = datetime.now(CR_TZ).strftime("%H:%M:%S")

            coolant_str = f"{coolant.value:.0f}°C" if coolant else "---"
            rpm_str = f"{rpm.value:.0f}" if rpm else "---"
            speed_str = f"{speed.value:.0f}km/h" if speed else "---"
            throttle_str = f"{throttle.value:.1f}%" if throttle else "---"
            pedal_str = f"{pedal.value:.1f}%" if pedal else "---"
            volts_str = f"{volts.value:.1f}V" if volts else "---"

            print(f"{time_str:<10} {coolant_str:<10} {rpm_str:<8} {speed_str:<8} {throttle_str:<10} {pedal_str:<8} {volts_str:<8}")

            reading_count += 1

            if coolant and coolant.value > 105:
                print(f"  🔥 WARNING: Coolant temp HIGH!")
            if coolant and coolant.value < 20:
                print(f"  ❄️  NOTE: Coolant reading very low - sensor issue?")

            time.sleep(interval)

        except Exception as e:
            print(f"  ⚠️  Read error: {e}")
            if logger:
                logger.log_event("ERROR", str(e))
            time.sleep(interval)

    # End session
    print("-" * 70)
    
    if logger:
        summary = logger.end_session()
        print(f"\n📊 Session Summary:")
        print(f"   File: {summary.get('file', 'N/A')}")
        print(f"   Duration: {summary.get('duration_seconds', 0):.1f} seconds")
        print(f"   Readings: {summary.get('reading_count', 0)}")
    else:
        print(f"\n📊 Monitor Summary:")
        print(f"   Stopped: {cr_timestamp()}")
        print(f"   Total readings: {reading_count}")


def run_freeze_frame(scanner: OBDScanner) -> None:
    """Read and display freeze frame data."""
    print_header("FREEZE FRAME DATA")
    print(f"  🕐 Read at: {cr_timestamp()}")
    
    freeze = scanner.read_freeze_frame()
    
    if not freeze:
        print("\n  ❌ No freeze frame data available")
        print("     (Freeze frame is captured when a DTC is stored)")
        return
    
    print(f"\n  📸 Freeze Frame for DTC: {freeze.dtc_code}")
    print(f"     Captured at the moment this code was set:\n")
    
    for reading in freeze.readings.values():
        print(f"  {reading.name}: {reading.value} {reading.unit}")
    
    print("\n" + "=" * 60)


def run_readiness(scanner: OBDScanner) -> None:
    """Read and display readiness monitor status."""
    print_header("READINESS MONITORS")
    print(f"  🕐 Read at: {cr_timestamp()}")
    
    # First show MIL status
    mil_on, dtc_count = scanner.get_mil_status()
    print(f"\n  Check Engine Light: {'🚨 ON' if mil_on else '✅ OFF'}")
    print(f"  Stored DTC Count: {dtc_count}")
    
    print_subheader("MONITOR STATUS")
    
    readiness = scanner.read_readiness()
    
    if not readiness:
        print("\n  ❌ Unable to read readiness monitors")
        return
    
    complete_count = 0
    incomplete_count = 0
    na_count = 0
    
    for name, status in readiness.items():
        if name == "MIL (Check Engine Light)":
            continue
        
        if not status.available:
            emoji = "➖"
            na_count += 1
        elif status.complete:
            emoji = "✅"
            complete_count += 1
        else:
            emoji = "❌"
            incomplete_count += 1
        
        print(f"  {emoji} {name}: {status.status_str}")
    
    print(f"\n  Summary:")
    print(f"    ✅ Complete: {complete_count}")
    print(f"    ❌ Incomplete: {incomplete_count}")
    print(f"    ➖ Not Available: {na_count}")
    
    if incomplete_count > 0:
        print("\n  💡 Note: Incomplete monitors need specific drive cycles to run.")
        print("     This is normal after clearing DTCs or disconnecting the battery.")
    
    print("\n" + "=" * 60)


def run_clear_codes(scanner: OBDScanner) -> None:
    """Clear all DTCs with confirmation."""
    print(f"\n⚠️  Clear DTCs requested at {cr_timestamp()}")
    print("   WARNING: This will also reset all readiness monitors!")
    confirm = input("   Continue? (yes/no): ")
    
    if confirm.strip().lower() == "yes":
        if scanner.clear_dtcs():
            print(f"✅ DTCs cleared successfully at {cr_timestamp()}")
            print("   Note: Readiness monitors have been reset.")
        else:
            print("❌ Failed to clear DTCs")
    else:
        print("Cancelled.")


def lookup_code(code: str) -> None:
    """Look up a single DTC code."""
    db = DTCDatabase()
    info = db.lookup(code)

    if info:
        print(f"\n{info.code}: {info.description}")
        print(f"  Category: {info.category}")
        print(f"  Type: {info.manufacturer}")
    else:
        print(f"\n{code}: Not found in database")


def run_demo() -> None:
    """Demo mode - no hardware required."""
    print_header("DEMO MODE - NO HARDWARE")
    print(f"  Timestamp: {cr_timestamp()}")
    print("\nThis shows what the scanner does without actual hardware.\n")

    db = DTCDatabase()
    print(f"📚 Database loaded: {db.count} codes\n")

    print("Codes that might cause your symptoms:")
    print("(ETC light + rough idle + fans always on + cold temp gauge)\n")

    relevant = ["P0118", "P2135", "P2122", "P1489", "P1490", "P0507", "P0128"]
    for code in relevant:
        info = db.lookup(code)
        if info:
            print(f"  {code}: {info.description}")

    print("\n" + "-" * 40)
    print("\nAvailable commands:")
    print("  --scan        Full diagnostic report")
    print("  --codes       Read trouble codes only")
    print("  --live        Single live data read")
    print("  --monitor     Continuous telemetry (Ctrl+C to stop)")
    print("  --monitor --log          ...with CSV logging")
    print("  --monitor --log --json   ...with JSON logging")
    print("  --freeze      Read freeze frame data")
    print("  --readiness   Check readiness monitors")
    print("  --lookup      Look up a specific code")

    print("\n📡 Available serial ports:")
    ports = ELM327.find_ports()
    if ports:
        for p in ports:
            print(f"  {p}")
    else:
        print("  No USB serial ports found")

    print("\nExamples:")
    print("  python3 jeep_scan.py --scan")
    print("  python3 jeep_scan.py --monitor --log")
    print("  python3 jeep_scan.py --freeze")


def connect_scanner(scanner: OBDScanner, port: Optional[str]) -> str:
    """Connect using a specified port, or auto-detect."""
    if port:
        scanner.elm.port = port
        print(f"\n📡 Connecting to {port}...")
        scanner.connect()
        return port

    ports = ELM327.find_ports()
    if not ports:
        raise ConnectionError("No USB serial ports found. Is the ELM327 plugged in?")

    last_error: Optional[Exception] = None

    print("\n🔍 Auto-detecting OBD port...")
    for p in ports:
        try:
            print(f"  Trying {p} ...")
            scanner.elm.port = p
            scanner.connect()
            print(f"  ✅ Vehicle responded on {p}")
            return p
        except Exception as e:
            last_error = e
            try:
                scanner.disconnect()
            except Exception:
                pass

    raise ConnectionError(
        f"No responding OBD device found. Tried: {ports}. Last error: {last_error}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Jeep OBD-II Scanner - Open Source Vehicle Diagnostics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 jeep_scan.py --demo                    # Demo mode
  python3 jeep_scan.py --scan                    # Full diagnostic report
  python3 jeep_scan.py --codes                   # DTCs only
  python3 jeep_scan.py --live                    # Live data (single read)
  python3 jeep_scan.py --monitor                 # Continuous telemetry
  python3 jeep_scan.py --monitor --log           # ...with CSV logging
  python3 jeep_scan.py --monitor --log --json    # ...with JSON logging
  python3 jeep_scan.py --freeze                  # Freeze frame data
  python3 jeep_scan.py --readiness               # Readiness monitors
  python3 jeep_scan.py --lookup P0118            # Look up code
  python3 jeep_scan.py --clear                   # Clear DTCs
        """,
    )

    parser.add_argument("--demo", action="store_true", help="Run demo mode (no hardware)")
    parser.add_argument("--scan", action="store_true", help="Full diagnostic scan")
    parser.add_argument("--codes", action="store_true", help="Read DTCs only")
    parser.add_argument("--live", action="store_true", help="Read live sensor data (single read)")
    parser.add_argument("--monitor", action="store_true", help="Continuous live telemetry (Ctrl+C to stop)")
    parser.add_argument("--log", action="store_true", help="Log monitor session to file")
    parser.add_argument("--json", action="store_true", help="Use JSON format for logging (default: CSV)")
    parser.add_argument("--interval", type=float, default=1.0, help="Refresh interval for --monitor (default: 1.0)")
    parser.add_argument("--freeze", action="store_true", help="Read freeze frame data")
    parser.add_argument("--readiness", action="store_true", help="Check readiness monitors")
    parser.add_argument("--clear", action="store_true", help="Clear all DTCs")
    parser.add_argument("--lookup", type=str, metavar="CODE", help="Look up a specific DTC code")
    parser.add_argument("--port", type=str, help="Serial port (auto-detect if not specified)")
    parser.add_argument("--baud", type=int, default=38400, help="Baud rate (default: 38400)")

    args = parser.parse_args()

    # Default to demo if no args
    if len(sys.argv) == 1:
        args.demo = True

    if args.demo:
        run_demo()
        return

    if args.lookup:
        lookup_code(args.lookup)
        return

    # Hardware operations
    scanner = OBDScanner(port=args.port, baudrate=args.baud)

    try:
        print(f"   Time: {cr_timestamp()}")
        used_port = connect_scanner(scanner, args.port)
        print("✅ Connected!\n")

        try:
            if args.scan:
                run_full_scan(scanner)
            elif args.codes:
                run_codes_only(scanner)
            elif args.live:
                run_live_data(scanner)
            elif args.monitor:
                log_format = "json" if args.json else "csv"
                run_monitor(scanner, args.interval, log=args.log, log_format=log_format)
            elif args.freeze:
                run_freeze_frame(scanner)
            elif args.readiness:
                run_readiness(scanner)
            elif args.clear:
                run_clear_codes(scanner)
            else:
                run_full_scan(scanner)
        finally:
            scanner.disconnect()
            print(f"\n🔌 Disconnected at {cr_timestamp()}")

    except ConnectionError as e:
        print(f"\n❌ Connection failed: {e}")
        print(f"   Time: {cr_timestamp()}")
        print("\n💡 Tips:")
        print("  - Make sure ELM327 is plugged into car's OBD port")
        print("  - Turn ignition to ON (engine can be off)")
        print("  - Try specifying port: --port /dev/tty.usbserial-XXXX")
        print("  - Run --demo to test without hardware")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"   Time: {cr_timestamp()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
