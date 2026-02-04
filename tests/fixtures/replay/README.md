Replay fixtures live in this folder.

Format:

{
  "meta": {
    "headers_on": true,
    "elm_version": "ELM327 v1.5",
    "protocol": "ISO 15765-4 CAN (11 bit, 500 kbaud)",
    "manufacturer": "generic"
  },
  "steps": [
    {"command": "ATDPN", "lines": ["A6"]},
    {"command": "0902", "lines": ["7E8 10 14 49 02 01 57 50 30 5A 5A 5A 39 39", "7E8 21 39 5A 54 53 33 39 32 31 32 33 34 35"]},
    {"command": "0101", "lines": ["7E8 06 41 01 80 07 A0 13"]}
  ],
  "expected": {
    "vehicle_info": {"vin": "WP0ZZZ99ZTS392123", "mil_on": "No", "dtc_count": "0"},
    "dtcs": ["P0420"],
    "readiness": {"Misfire": {"available": true, "complete": true}}
  }
}

Build from raw logs:

python3 tools/replay_fixture_builder.py --input logs/obd_raw.log --output tests/fixtures/replay/obd_scan.json

Then edit the fixture to:
- Remove commands not used by the test sequence.
- Fill in meta and expected sections.
