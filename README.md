# OBD-II Diagnostics AI CLI

![OBD-II Diagnostics AI CLI Banner](https://img.shields.io/badge/OBD--II%20Diagnostics-AI%20CLI-0f172a?style=for-the-badge&logo=terminal&logoColor=white)

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![OpenAI](https://img.shields.io/badge/AI-OpenAI-412991?style=flat-square&logo=openai&logoColor=white)
![ELM327](https://img.shields.io/badge/Adapter-ELM327-0ea5e9?style=flat-square&logo=usb&logoColor=white)
![CSV](https://img.shields.io/badge/Logs-CSV-10b981?style=flat-square&logo=files&logoColor=white)
![JSON](https://img.shields.io/badge/Reports-JSON-f97316?style=flat-square&logo=json&logoColor=white)
![CLI](https://img.shields.io/badge/Interface-CLI-111827?style=flat-square&logo=gnubash&logoColor=white)

**Commercial-grade** diagnostics CLI for OBD-II vehicles with real-time telemetry, AI-assisted reporting, and a built-in paywall/credits flow for monetized deployments.

---

## Highlights

- **Menu-first CLI** designed for fast technician workflows
- **Full diagnostic scan** with stored, pending, and permanent DTCs
- **Live telemetry** with configurable refresh rate and exportable sessions
- **Freeze frames** captured at fault time
- **Readiness monitors** for inspection checks
- **AI diagnostic reports** for scan summaries and next-step guidance
- **Credits-based monetization** with checkout redirects and usage gating
- **Multi-manufacturer DTC databases** (Chrysler/Jeep/Dodge, Land Rover/Jaguar)

---

## Technology Flags

- 🐍 **Python 3.8+** runtime
- 🤖 **OpenAI** report generation (configurable model)
- 🔌 **ELM327** adapter support over USB/Bluetooth
- 📊 **CSV/JSON** logging and report persistence
- 🧭 **Interactive CLI** menus and configuration
- 💳 **Paywall** client for credits and checkout flows

---

## Requirements

- Python 3.8+
- ELM327 USB/Bluetooth adapter
- OBD-II compliant vehicle (1996+ US, 2001+ EU)

---

## Installation

Access to this repository is provided to licensed customers. Once access is granted:

```bash
pip install -r requirements.txt
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

```
  ╔════════════════════════════════════════════════════════╗
  ║           OBD-II Diagnostics AI CLI                   ║
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

## Configuration

### Settings Menu

Open settings by pressing `S` in the main menu.

- **Vehicle Make** — Generic, Chrysler/Jeep/Dodge, Land Rover/Jaguar
- **Log Format** — CSV or JSON
- **Monitor Interval** — 0.5s to 10s refresh rate
- **View Serial Ports** — USB serial device list
- **Paywall / Credits** — Configure API base + checkout flow

### AI Reports

Reports are generated from full scans and stored as JSON in `data/reports/`.

```bash
export OPENAI_API_KEY="your-key-here"
# Optional: override model (default is gpt-4o-mini)
export OPENAI_MODEL="gpt-4o-mini"
```

### Paywall (Credits Service)

```bash
export PAYWALL_API_BASE="https://api.yourdomain.com"
```

For local testing, bypass paywall enforcement:

```bash
export OBD_SUPERUSER=1
```

---

## Project Structure

```
obd2-diagnostics-ai-cli/
├── app/                     # Menu-first CLI implementation
├── requirements.txt         # Python dependencies
├── README.md
├── data/
│   ├── dtc_generic.csv          # Generic OBD-II codes (3,000+)
│   ├── dtc_jeep_dodge_chrysler.csv  # Chrysler/Jeep/Dodge specific
│   ├── dtc_land_rover.csv       # Land Rover/Jaguar specific
│   ├── i18n/                    # CLI language packs
│   ├── reports/                 # Saved AI reports
│   └── uds/                     # UDS DID/module/routine definitions
├── logs/                    # Session logs (auto-created)
│   └── session_YYYY-MM-DD_HH-MM-SS.csv
├── openai/                  # OpenAI integrations
├── paywall/                 # Paywall client, config, and CLI menu
└── obd/
    ├── __init__.py          # Package exports
    ├── elm/elm327.py        # ELM327 adapter communication
    ├── obd2/scanner.py      # High-level scanner interface
    ├── dtc/database.py      # DTC decoding and database lookup
    ├── pids/standard_mode01.py  # OBD-II PID definitions
    ├── logger.py            # Session logging (CSV/JSON)
    └── utils.py             # Shared utilities
```

---

## Output Guide

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

## Supported PIDs (Sample)

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

## Custom Codes

DTC databases are CSV files in the `data/` folder.

```csv
# Comment lines start with #
"CODE","Description"
"P1234","Your custom code description"
```

To add a new manufacturer:

1. Create `data/dtc_yourmanufacturer.csv`
2. Add the mapping in `obd/dtc.py` under `MANUFACTURER_FILES`
3. Select it in **Settings → Vehicle Make**

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

## Commercial Terms

This project is maintained as a commercial product with monetization support. For licensing, pricing, or deployment assistance, contact the product owner.
