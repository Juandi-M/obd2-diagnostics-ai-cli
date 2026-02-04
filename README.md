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

## Commercial Notice

This is a **commercial application**. Source is provided for licensed or internal use. It is **not** offered as open source. If you need a commercial license, contact the project owner.

---

## Table of Contents

- [What This App Does](#what-this-app-does)
- [Technical Specs](#technical-specs)
  - [Adapters and Transports](#adapters-and-transports)
  - [Communication Lines and Buses](#communication-lines-and-buses)
  - [Supported Protocols](#supported-protocols)
- [Features (By Area)](#features-by-area)
- [How to Run](#how-to-run)
  - [Install](#install)
  - [CLI](#cli)
  - [GUI (Qt)](#gui-qt)
  - [Demo Mode](#demo-mode)
- [Environment (.env)](#environment-env)
- [Testing](#testing)
- [Output Locations](#output-locations)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## What This App Does

This application is a full OBD-II diagnostic workflow in a clean-architecture codebase:

- Connect to an OBD-II adapter and identify the vehicle interface.
- Read and decode diagnostic trouble codes (stored, pending, permanent).
- Run a full diagnostic scan and summarize results.
- View readiness monitor state for emissions systems.
- Stream live data (RPM, speed, coolant temp, etc.).
- Capture freeze frame snapshots.
- Perform UDS discovery and related tooling on supported ECUs.
- Generate AI diagnostic reports from scan results.
- Store logs and reports locally for later review.

It ships with a CLI (primary) and a Qt GUI (work in progress but functional).

---

## Technical Specs

### Adapters and Transports

The app communicates through **ELM327-compatible adapters** that expose a serial interface. Common options:

- **USB ELM327** (recommended for stability and throughput)
- **Bluetooth (SPP)** adapters that appear as a serial port
- **Other serial bridges** that present a `/dev/tty*` / COM port

The software expects a serial-style ELM-compatible interface and uses AT commands to configure protocol and headers.

### Communication Lines and Buses

Different vehicles expose different physical OBD-II buses. This app supports the common ones via the adapter:

- **CAN (ISO 15765-4)** - two-wire differential bus (CAN-H / CAN-L)
- **K-Line (legacy protocol)** - single-wire line used on older vehicles
- **L-Line** - optional wake-up line (rarely required, older platforms)
- **J1850 VPW/PWM** - older GM/Ford buses (adapter-dependent)

### Supported Protocols

The app targets standard OBD-II and common UDS workflows:

- **OBD-II modes** (e.g., Mode 01, 02, 03, 07, 0A)
- **ISO 15765-4 (CAN)** for modern vehicles
- **ISO 9141-2 / KWP2000 (K-Line)** fallback on older vehicles
- **UDS (ISO 14229)** tooling where supported by the ECU

Protocol selection is handled by the adapter and the infrastructure layer, with explicit K-Line support when available.

---

## Features (By Area)

### Connection and Vehicle Detection

- Detect available serial ports
- Connect/disconnect with clear status feedback
- Choose manufacturer context (Generic, Chrysler/Jeep/Dodge, Land Rover/Jaguar)

### Diagnostic Trouble Codes (DTCs)

- Read **stored**, **pending**, and **permanent** codes
- Decode DTCs using built-in databases (multi-brand)
- Lookup and search codes by ID or text

### Full Diagnostic Scan

- One-command scan across supported systems
- Summarized output with timing and counts
- Saves scan output for AI reports and review

### Live Telemetry

- Real-time PID streaming
- Configurable refresh rate
- Optional session logging

### Freeze Frame

- Capture snapshot data recorded at fault time

### Readiness Monitors

- Visual status of emissions-related monitors
- Useful for inspection readiness

### UDS Tools

- UDS module discovery
- ECU metadata and capability probing

### AI Diagnostic Reports

- Generate structured AI summaries from scans
- Reports stored locally as JSON

### Logging & Reports

- Logs saved under `logs/`
- AI reports saved under `data/reports/`

---

## How to Run

### Install

```bash
# Clone the repository
# (Use your internal or licensed source repository)

git clone <repo-url>
cd obd2-diagnostics-ai-cli

# Optional: create a venv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### CLI

```bash
# Interactive CLI
python3 -m app_cli

# Help
python3 -m app_cli --help
```

### GUI (Qt)

```bash
python3 -m app_gui
```

### Demo Mode

```bash
# Run without hardware
python3 -m app_cli --demo
```

---

## Environment (.env)

Configuration is handled via environment variables or a local `.env` file (see `.env.example`). Keep this file out of source control.

At a high level, the `.env` contains:

- Service endpoints (AI reporting backend, billing/credits, optional gateways)
- API keys and secrets for integrations
- Runtime toggles for diagnostics/logging
- Development overrides (demo mode, superuser bypass, etc.)

---

## Testing

This repo uses `unittest` and a set of focused suites. Tests are intentionally offline and deterministic unless noted.

### 1) Application + Domain unit tests (pure logic)

What they cover:
- State transitions, settings load/save, vehicle brand selection
- i18n translation behavior
- AI report helpers (language detect, JSON extraction, report status updates)
- Use case orchestration (connection, scans, reports, UDS tools)

Where:
- `tests/test_application_state.py`
- `tests/test_application_settings.py`
- `tests/test_application_vehicle.py`
- `tests/test_application_i18n.py`
- `tests/test_application_ai_report.py`
- `tests/test_application_paywall.py`
- `tests/test_application_services.py`

Run:
```bash
python3 -m unittest -v \
  tests.test_application_state \
  tests.test_application_settings \
  tests.test_application_vehicle \
  tests.test_application_i18n \
  tests.test_application_ai_report \
  tests.test_application_paywall \
  tests.test_application_services
```

### 2) Infrastructure adapter tests (mocked I/O)

What they cover:
- AI adapter error mapping and request plumbing
- Paywall adapter error mapping and bypass logic
- Persistence adapters (settings, VIN cache, reports)
- Reporting adapters (PDF path, renderer delegation)
- i18n repository load

Where:
- `tests/test_infra_ai_adapters.py`
- `tests/test_infra_ai_report.py`
- `tests/test_infra_paywall_adapter.py`
- `tests/test_infra_persistence_settings.py`
- `tests/test_infra_persistence_vin_cache.py`
- `tests/test_infra_persistence_reports.py`
- `tests/test_infra_persistence_document_paths.py`
- `tests/test_infra_reporting_pdf_paths.py`
- `tests/test_infra_reporting_pdf_renderer.py`
- `tests/test_infra_i18n_repository.py`

Run:
```bash
python3 -m unittest -v \
  tests.test_infra_ai_adapters \
  tests.test_infra_ai_report \
  tests.test_infra_paywall_adapter \
  tests.test_infra_persistence_settings \
  tests.test_infra_persistence_vin_cache \
  tests.test_infra_persistence_reports \
  tests.test_infra_persistence_document_paths \
  tests.test_infra_reporting_pdf_paths \
  tests.test_infra_reporting_pdf_renderer \
  tests.test_infra_i18n_repository
```

### 3) Presentation smoke + cancellation tests (CLI/Qt)

What they cover:
- CLI help flag
- CLI smoke flow (connect, full scan, report, export PDF) with fakes
- CLI live monitor cancel path
- Qt live monitor start/stop (skips if PySide6 unavailable)

Where:
- `tests/test_cli_smoke.py`
- `tests/test_cancellation.py`

Run:
```bash
python3 -m unittest -v tests.test_cli_smoke tests.test_cancellation
```

### 4) Resilience and failure mode tests

What they cover:
- NO DATA retry behavior
- Partial frame handling
- Timeout mapping to scanner errors
- Disconnect mid-scan handling and state cleanup

Where:
- `tests/test_failure_modes.py`

Run:
```bash
python3 -m unittest -v tests.test_failure_modes
```

### 5) Replay-based protocol tests (OBD/UDS)

What they cover:
- Deterministic scan results using captured ELM/OBD transcripts
- UDS discovery and DID decoding from recorded sessions

Where:
- `tests/replay_transport.py` (replay transport)
- `tests/test_replay_obd.py`
- `tests/test_replay_uds.py`
- `tests/fixtures/replay/` (fixtures)
- `tools/replay_fixture_builder.py` (build fixtures from logs)

Run (fixtures required):
```bash
python3 -m unittest -v tests.test_replay_obd tests.test_replay_uds
```

Build a fixture from a raw log:
```bash
python3 tools/replay_fixture_builder.py \
  --input logs/obd_raw.log \
  --output tests/fixtures/replay/obd_scan.json
```

### 6) Schema + contract tests

What they cover:
- Scan report JSON shape stays consistent
- Adapter classes expose required methods

Where:
- `tests/test_scan_report_schema.py`
- `tests/test_ports_contracts.py`

Run:
```bash
python3 -m unittest -v tests.test_scan_report_schema tests.test_ports_contracts
```

---

## Output Locations

Runtime output is written to:

- `logs/` - session logs and raw adapter logs
- `data/reports/` - AI diagnostic reports (JSON)

These directories are auto-created at runtime.

---

## Project Structure

```
obd2-diagnostics-ai-cli/
|-- app/                     # Clean architecture layers
|   |-- domain
|   |-- application
|   |-- infrastructure
|   `-- presentation
|-- app_cli/                 # CLI entrypoint (thin wrapper)
|-- app_gui/                 # Qt entrypoint (thin wrapper)
|-- data/                    # Static data (DTC, UDS, i18n)
|-- logs/                    # Runtime logs (auto-created)
|-- obd/                     # OBD protocol library
|-- requirements.txt
`-- tools/
```

---

## Troubleshooting

### "No USB serial ports found"

- Check USB connection
- Verify adapter is plugged into the vehicle OBD port
- On macOS, check System Settings -> Security for permission

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
# Check Device Manager -> Ports (COM & LPT)
```

---

## License

Commercial / proprietary. All rights reserved. This repository is provided under a commercial license agreement.
