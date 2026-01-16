# OBD-II Scanner

Open source, modular vehicle diagnostic tool. Read trouble codes, monitor live telemetry, and analyze vehicle data from any OBD-II compliant vehicle (1996+).

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-macOS%20|%20Linux%20|%20Windows-lightgrey.svg)

---

## Features

- **Read Diagnostic Trouble Codes (DTCs)** — Stored, pending, and permanent codes
- **Live Telemetry Monitoring** — Real-time sensor data with configurable refresh rate
- **Freeze Frame Data** — Snapshot of sensor values when a code was triggered
- **Readiness Monitors** — Check emission system self-test status (useful for inspections)
- **Session Logging** — Export monitoring sessions to CSV or JSON for later analysis
- **Multi-Brand Support** — Manufacturer-specific code databases (Chrysler, Land Rover, etc.)
- **15,000+ DTC Definitions** — Comprehensive code database with descriptions

---

## Requirements

- Python 3.8+
- ELM327 USB/Bluetooth adapter
- OBD-II compliant vehicle (1996+ for US, 2001+ for EU)

---

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/obd2-scanner.git
cd obd2-scanner

# Install dependencies
pip install pyserial
```

---

## Quick Start

```bash
# Run interactive mode (recommended)
python3 obd_scan.py

# Or use command flags
python3 obd_scan.py --scan
```

---

## Usage

### Interactive Mode

Simply run without arguments for the interactive menu:

```bash
python3 obd_scan.py
```

### Command Line Flags

| Flag | Description |
|------|-------------|
| `--scan` | Full diagnostic scan (DTCs + readiness + live data) |
| `--codes` | Read trouble codes only |
| `--live` | Single read of live sensor data |
| `--monitor` | Continuous telemetry monitoring (Ctrl+C to stop) |
| `--freeze` | Read freeze frame data |
| `--readiness` | Check readiness monitor status |
| `--clear` | Clear all DTCs (resets readiness monitors) |
| `--lookup CODE` | Look up a specific DTC (e.g., `--lookup P0118`) |
| `--demo` | Demo mode without hardware |

### Options

| Option | Description |
|--------|-------------|
| `--port PORT` | Serial port (auto-detect if not specified) |
| `--make MAKE` | Vehicle make for manufacturer-specific codes: `chrysler`, `landrover`, `ford`, `gm`, `toyota` |
| `--log` | Save monitoring session to file |
| `--json` | Use JSON format for logging (default: CSV) |
| `--interval N` | Refresh interval in seconds for monitoring (default: 1.0) |
| `--baud RATE` | Baud rate (default: 38400) |

### Examples

```bash
# Full diagnostic scan
python3 obd_scan.py --scan

# Scan with Chrysler-specific codes
python3 obd_scan.py --scan --make chrysler

# Monitor with logging every 0.5 seconds
python3 obd_scan.py --monitor --interval 0.5 --log

# Monitor and save as JSON
python3 obd_scan.py --monitor --log --json

# Check readiness for emissions inspection
python3 obd_scan.py --readiness

# Look up a specific code
python3 obd_scan.py --lookup P0118

# Specify serial port manually
python3 obd_scan.py --port /dev/tty.usbserial-11230 --scan
```

---

## Project Structure

```
obd2-scanner/
├── obd_scan.py              # Main CLI / Interactive menu
├── requirements.txt         # Python dependencies
├── README.md
├── data/
│   ├── dtc_generic.csv      # Generic OBD-II codes (P0xxx, P2xxx, U0xxx)
│   ├── dtc_chrysler.csv     # Chrysler/Jeep/Dodge specific (P1xxx)
│   └── dtc_landrover.csv    # Land Rover/Jaguar specific (P1xxx)
├── logs/                    # Session logs (auto-created)
│   └── session_YYYY-MM-DD_HH-MM-SS.csv
└── obd/
    ├── __init__.py          # Package exports
    ├── elm327.py            # ELM327 adapter communication
    ├── scanner.py           # High-level scanner interface
    ├── dtc.py               # DTC decoding and database lookup
    ├── pids.py              # OBD-II PID definitions and formulas
    └── logger.py            # Session logging (CSV/JSON)
```

---

## Understanding the Output

### DTC Status Types

| Status | Icon | Meaning |
|--------|------|---------|
| **Stored** | 🚨 | Confirmed fault, MIL (Check Engine) is ON |
| **Pending** | ⚠️ | Fault detected once, ECU is monitoring |
| **Permanent** | ⚠️ | Cannot be cleared manually, requires repair + drive cycles |

### Readiness Monitors

| Status | Icon | Meaning |
|--------|------|---------|
| **Complete** | ✅ | Self-test has run and passed |
| **Incomplete** | ❌ | Self-test has not run yet |
| **N/A** | ➖ | Not supported by this vehicle |

---

## Supported PIDs

| PID | Sensor | Unit |
|-----|--------|------|
| 05 | Engine Coolant Temperature | °C |
| 0C | Engine RPM | rpm |
| 0D | Vehicle Speed | km/h |
| 11 | Throttle Position | % |
| 42 | Control Module Voltage | V |
| 0B | Intake Manifold Pressure | kPa |
| 04 | Calculated Engine Load | % |
| 06 | Short Term Fuel Trim | % |
| 07 | Long Term Fuel Trim | % |
| 0F | Intake Air Temperature | °C |
| 10 | MAF Air Flow Rate | g/s |
| 2F | Fuel Tank Level | % |

---

## Adding Custom Codes

DTC databases are stored as CSV files in the `data/` folder.

### Format

```csv
# Comment lines start with #
"CODE","Description"
"P1234","Your custom code description"
```

### Example

```csv
# Custom codes for my vehicle
"P1489","High Speed Fan Control Relay Circuit"
"P1490","Low Speed Fan Control Relay Circuit"
```

---

## Troubleshooting

### "No ELM327 adapter found"

- Check USB connection
- Verify adapter is plugged into vehicle OBD port
- Turn ignition to ON (engine can be off)
- Try specifying port manually: `--port /dev/tty.usbserial-XXXX`

### "No response from vehicle ECU"

- Ensure ignition is ON
- Check OBD port connection (should click in firmly)
- Try with engine running
- Some vehicles need 10-15 seconds after ignition ON

### "Failed to clear DTCs"

- Some codes are **permanent** and cannot be cleared manually
- Try with engine running
- Permanent codes clear automatically after repair + drive cycles

### Finding your serial port

```bash
# macOS
ls /dev/tty.usb*

# Linux
ls /dev/ttyUSB*

# Windows
# Check Device Manager → Ports (COM & LPT)
```

---

## Roadmap

- [x] Basic DTC reading (Mode 03, 07, 0A)
- [x] Live data monitoring (Mode 01)
- [x] Freeze frame data (Mode 02)
- [x] Readiness monitors
- [x] Session logging (CSV/JSON)
- [x] Multi-brand code databases
- [ ] Interactive menu interface
- [ ] ABS/Airbag module support
- [ ] Bi-directional controls (brake service mode, etc.)
- [ ] GUI dashboard

---

## Contributing

Contributions welcome! Especially:

- DTC databases for other manufacturers
- Protocol documentation for ABS/Airbag modules
- Bi-directional command research

---

## Disclaimer

This tool is for **educational and diagnostic purposes only**. Clearing codes does not fix problems. Always repair the underlying issue. The authors are not responsible for any damage caused by misuse.

---

## License

MIT License — Do whatever you want with it.

---

## Acknowledgments

- OBD-II standard: SAE J1979
- DTC definitions: SAE J2012
- ELM327 datasheet
- Various OBD forums and communities