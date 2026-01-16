"""
DTC (Diagnostic Trouble Code) Module
====================================
Handles DTC decoding, lookup, and database management.
Supports # comments in CSV files for section headers.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict


@dataclass(frozen=True)
class DTCInfo:
    """Represents a Diagnostic Trouble Code."""
    code: str
    description: str


def _project_root() -> Path:
    """
    Resolve repo root reliably regardless of where python is executed from.

    Expected layout:
      JeepOBDII/
        data/dtc_database.csv
        obd/dtc.py   (this file)
    """
    return Path(__file__).resolve().parents[1]


def _default_csv_path() -> Path:
    return _project_root() / "data" / "dtc_database.csv"


class DTCDatabase:
    """
    DTC lookup database.
    Loads codes from CSV for easy extension.
    
    CSV Format:
        "CODE","Description"
        
    Supports:
        - # comments for section headers
        - Empty lines for spacing
    """

    def __init__(self, csv_path: Optional[str] = None):
        self.codes: Dict[str, DTCInfo] = {}

        self.path: Path = Path(csv_path) if csv_path else _default_csv_path()

        # Load if it exists; otherwise keep empty DB (avoid crashing tools)
        if self.path.exists():
            self.load_from_csv(self.path)

    def load_from_csv(self, csv_path: Path | str):
        """Load DTC codes from CSV file."""
        p = Path(csv_path)

        with p.open("r", encoding="utf-8-sig", newline="") as f:
            for line in f:
                # Strip whitespace
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Skip comments (lines starting with #)
                if line.startswith("#"):
                    continue
                
                # Parse CSV line
                try:
                    # Handle quoted CSV format: "CODE","Description"
                    reader = csv.reader([line])
                    row = next(reader)
                    
                    if len(row) < 2:
                        continue
                    
                    code = row[0].strip().upper()
                    description = row[1].strip()
                    
                    if not code:
                        continue
                    
                    self.codes[code] = DTCInfo(
                        code=code,
                        description=description,
                    )
                except Exception:
                    # Skip malformed lines
                    continue

    def lookup(self, code: str) -> Optional[DTCInfo]:
        """Look up a DTC code."""
        key = (code or "").strip().upper()
        return self.codes.get(key)

    def get_description(self, code: str) -> str:
        """Get description for a code, with fallback."""
        info = self.lookup(code)
        return info.description if info else "Unknown code - not in database"

    def search(self, query: str) -> List[DTCInfo]:
        """Search codes by description or code."""
        q = (query or "").strip().lower()
        if not q:
            return []
        return [
            info
            for info in self.codes.values()
            if q in (info.description or "").lower() or q in (info.code or "").lower()
        ]

    @property
    def count(self) -> int:
        """Number of codes in database."""
        return len(self.codes)


def decode_dtc_bytes(hex_bytes: str) -> str:
    """
    Convert raw DTC hex bytes to standard format.

    Args:
        hex_bytes: 4 character hex string (e.g., "0118")

    Returns:
        Formatted DTC code (e.g., "P0118")
    """
    if len(hex_bytes) != 4:
        return f"INVALID:{hex_bytes}"

    try:
        first_nibble = int(hex_bytes[0], 16)

        type_bits = (first_nibble >> 2) & 0x03
        prefixes = {0: "P", 1: "C", 2: "B", 3: "U"}
        prefix = prefixes.get(type_bits, "P")

        second_char = str(first_nibble & 0x03)
        rest = hex_bytes[1:].upper()

        return f"{prefix}{second_char}{rest}"

    except ValueError:
        return f"INVALID:{hex_bytes}"


def parse_dtc_response(response: str, mode: str = "03") -> List[str]:
    """
    Parse DTC response from ECU.

    Mode 03: Stored (43)
    Mode 07: Pending (47)
    Mode 0A: Permanent (4A)
    """
    dtcs: List[str] = []

    prefixes = {"03": "43", "07": "47", "0A": "4A"}
    prefix = prefixes.get(mode, "43")

    resp = (response or "").replace(" ", "").upper()

    if prefix in resp:
        resp = resp.replace(prefix, "", 1)

    for i in range(0, len(resp), 4):
        chunk = resp[i : i + 4]
        if len(chunk) < 4:
            continue
        if chunk == "0000":
            continue

        dtc_code = decode_dtc_bytes(chunk)
        if not dtc_code.startswith("INVALID"):
            dtcs.append(dtc_code)

    return dtcs


_default_db: Optional[DTCDatabase] = None


def get_database() -> DTCDatabase:
    """Get the default DTC database instance."""
    global _default_db
    if _default_db is None:
        _default_db = DTCDatabase()
    return _default_db


def lookup_code(code: str) -> str:
    """Quick lookup for a single code."""
    db = get_database()
    return db.get_description(code)