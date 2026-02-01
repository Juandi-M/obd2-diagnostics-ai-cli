# OBD-II Scanner

Open source, modular vehicle diagnostic tool with interactive menu. Read trouble codes, monitor live telemetry, and analyze vehicle data from any OBD-II compliant vehicle (1996+).

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-macOS%20|%20Linux%20|%20Windows-lightgrey.svg)

---

## Features

- **Interactive Menu** — No flags to memorize, just pick from the menu
- **Read Diagnostic Trouble Codes (DTCs)** — Stored, pending, and permanent codes
- **Live Telemetry Monitoring** — Real-time sensor data with configurable refresh rate
- **Freeze Frame Data** — Snapshot of sensor values when a code was triggered
- **Readiness Monitors** — Check emission system self-test status (useful for inspections)
- **Session Logging** — Export monitoring sessions to CSV or JSON
- **Multi-Brand Support** — Chrysler/Jeep/Dodge, Land Rover/Jaguar code databases
- **3,000+ DTC Definitions** — Comprehensive code database with descriptions

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
python3 -m app

# Or run demo mode without hardware
python3 -m app --demo
```

---

## Interactive Menu

Simply run `python3 -m app` to see the interactive menu:

```
  ╔════════════════════════════════════════════════════════╗
  ║           OBD-II Scanner v2.0.0                        ║
  ╚════════════════════════════════════════════════════════╝

  Status: 🔴 Disconnected | Vehicle: Generic | Format: CSV

  ╔══════════════════════════════════════════════════════════╗
  ║  MAIN MENU                                               ║
  ╠══════════════════════════════════════════════════════════╣
  ║  1. Connect to Vehicle                                   ║
  ║  2. Disconnect                                           ║
  ║  3. Full Diagnostic Scan                                 ║
  ║  4. Read Trouble Codes                                   ║
  ║  5. Live Telemetry Monitor                               ║
  ║  6. Freeze Frame Data                                    ║
  ║  7. Readiness Monitors                                   ║
  ║  8. Clear Codes                                          ║
  ║  9. Lookup Code                                          ║
  ║ 10. Search Codes                                         ║
  ║ 11. UDS Tools                                            ║
  ║ 12. AI Diagnostic Report                                 ║
  ║  S. Settings                                             ║
  ║  0. Exit                                                 ║
  ╚══════════════════════════════════════════════════════════╝

  Select option: _
```

---

## Settings

Access settings by pressing `S` in the main menu:

- **Vehicle Make** — Switch between Generic, Chrysler/Jeep/Dodge, or Land Rover/Jaguar
- **Log Format** — Choose CSV or JSON for session logs
- **Monitor Interval** — Adjust refresh rate for live telemetry (0.5s - 10s)
- **View Serial Ports** — See available USB serial ports
- **Paywall / Stripe** — Configure Stripe checkout settings

---

## AI Reports (OpenAI)

The CLI can generate AI diagnostic reports from a full scan. Reports are stored
as JSON files under `data/reports/` and can be re-opened from the CLI.

### Configuration

Set your API key before running the CLI:

```bash
export OPENAI_API_KEY="your-key-here"
# Optional: override model (default is gpt-4o-mini)
export OPENAI_MODEL="gpt-4o-mini"
```

---

## Paywall (Stripe placeholder)

The CLI includes a placeholder Stripe checkout flow under **Settings → Paywall / Stripe**.
Configure the following environment variable and fields before starting a checkout:

```bash
export STRIPE_API_KEY="your-stripe-key"
```

Then set a Stripe price ID and success/cancel URLs inside the paywall menu.

---

## Project Structure

```
obd2-scanner/
├── app/                     # Menu-first CLI implementation
├── requirements.txt         # Python dependencies
├── README.md
├── data/
│   ├── dtc_generic.csv          # Generic OBD-II codes (3,000+)
│   ├── dtc_jeep_dodge_Chrysler.csv  # Chrysler/Jeep/Dodge specific
│   ├── dtc_landrover.csv        # Land Rover/Jaguar specific
│   ├── i18n/                    # CLI language packs
│   ├── paywall.json             # Paywall configuration
│   ├── reports/                 # Saved AI reports
│   └── uds/                     # UDS DID/module/routine definitions
├── logs/                    # Session logs (auto-created)
│   └── session_YYYY-MM-DD_HH-MM-SS.csv
├── openai/                  # OpenAI and Stripe integrations
└── obd/
    ├── __init__.py          # Package exports
    ├── elm327.py            # ELM327 adapter communication
    ├── scanner.py           # High-level scanner interface
    ├── dtc.py               # DTC decoding and database lookup
    ├── pids.py              # OBD-II PID definitions
    ├── logger.py            # Session logging (CSV/JSON)
    └── utils.py             # Shared utilities
```

---

## Understanding the Output

### DTC Status Types

| Status | Icon | Meaning |
|--------|------|---------|
| **Stored** | 🚨 | Confirmed fault, Check Engine light is ON |
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
| 06 | Short Term Fuel Trim | % |
| 07 | Long Term Fuel Trim | % |
| 49 | Accelerator Pedal Position D | % |
| 4A | Accelerator Pedal Position E | % |

---

## Adding Custom Codes

DTC databases are CSV files in the `data/` folder.

### Format

```csv
# Comment lines start with #
"CODE","Description"
"P1234","Your custom code description"
```

### Adding a New Manufacturer

1. Create `data/dtc_yourmanufacturer.csv`
2. Add the mapping in `obd/dtc.py` under `MANUFACTURER_FILES`
3. The codes will be available in Settings → Vehicle Make

---

## Troubleshooting

### "No USB serial ports found"

- Check USB connection
- Verify adapter is plugged into vehicle OBD port
- On macOS, check System Preferences → Security for permission

### "No response from vehicle ECU"

- Turn ignition to ON (or start engine)
- Check OBD port connection (should click in firmly)
- Wait 10-15 seconds after turning ignition ON

### "Failed to clear DTCs"

- **Permanent codes** cannot be cleared manually
- They clear automatically after repair + successful drive cycles

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
- [x] Interactive menu interface
- [ ] ABS/Airbag module support
- [ ] Bi-directional controls (brake service mode, etc.)
- [ ] GUI dashboard

---

## License

MIT License — Do whatever you want with it.

---

## Acknowledgments

- OBD-II standard: SAE J1979
- DTC definitions: SAE J2012
- ELM327 datasheet
