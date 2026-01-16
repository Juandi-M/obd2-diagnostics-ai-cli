"""
DTC (Diagnostic Trouble Code) Module
====================================
Handles DTC decoding, lookup, and database management.
Supports # comments in CSV files for section headers.
Loads all CSV files from data/ directory automatically.
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
    source: str = ""  # Which CSV file it came from


def _project_root() -> Path:
    """
    Resolve repo root reliably regardless of where python is executed from.
    """
    return Path(__file__).resolve().parents[1]


def _data_dir() -> Path:
    return _project_root() / "data"


class DTCDatabase:
    """
    DTC lookup database.
    Loads codes from all CSV files in data/ directory.
    
    CSV Format:
        "CODE","Description"
        
    Supports:
        - # comments for section headers
        - Empty lines for spacing
        - Multiple CSV files (generic + manufacturer-specific)
    """

    # Map of manufacturer keywords to their CSV files
    MANUFACTURER_FILES = {
        "chrysler": "dtc_jeep_dodge_Chrysler.csv",
        "jeep": "dtc_jeep_dodge_Chrysler.csv",
        "dodge": "dtc_jeep_dodge_Chrysler.csv",
        "landrover": "dtc_landrover.csv",
        "jaguar": "dtc_landrover.csv",
    }

    def __init__(self, manufacturer: Optional[str] = None):
        """
        Initialize DTC database.
        
        Args:
            manufacturer: Optional manufacturer name to load specific codes.
                         If None, loads generic + all manufacturer codes.
        """
        self.codes: Dict[str, DTCInfo] = {}
        self.manufacturer = manufacturer
        self._load_databases()

    def _load_databases(self):
        """Load all relevant CSV databases."""
        data_dir = _data_dir()
        
        if not data_dir.exists():
            return
        
        # Always load generic codes first
        generic_path = data_dir / "dtc_generic.csv"
        if generic_path.exists():
            self._load_from_csv(generic_path, "generic")
        
        # Load manufacturer-specific codes (they override generic for P1xxx codes)
        if self.manufacturer:
            # Load only the specified manufacturer
            mfr_lower = self.manufacturer.lower()
            if mfr_lower in self.MANUFACTURER_FILES:
                mfr_file = data_dir / self.MANUFACTURER_FILES[mfr_lower]
                if mfr_file.exists():
                    self._load_from_csv(mfr_file, mfr_lower)
        else:
            # Load all manufacturer files
            for mfr_name, filename in self.MANUFACTURER_FILES.items():
                mfr_path = data_dir / filename
                if mfr_path.exists():
                    self._load_from_csv(mfr_path, mfr_name)

    def _load_from_csv(self, csv_path: Path, source: str):
        """Load DTC codes from a single CSV file."""
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                
                try:
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
                        source=source,
                    )
                except Exception:
                    continue

    def set_manufacturer(self, manufacturer: str):
        """
        Change manufacturer and reload databases.
        Useful for switching between brands in interactive mode.
        """
        self.manufacturer = manufacturer
        self.codes.clear()
        self._load_databases()

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
    
    @property
    def available_manufacturers(self) -> List[str]:
        """List of available manufacturer databases."""
        data_dir = _data_dir()
        available = []
        seen_files = set()
        
        for mfr, filename in self.MANUFACTURER_FILES.items():
            if filename not in seen_files and (data_dir / filename).exists():
                available.append(mfr)
                seen_files.add(filename)
        
        return available


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


def get_database(manufacturer: Optional[str] = None) -> DTCDatabase:
    """Get the default DTC database instance."""
    global _default_db
    if _default_db is None or manufacturer:
        _default_db = DTCDatabase(manufacturer=manufacturer)
    return _default_db


def lookup_code(code: str) -> str:
    """Quick lookup for a single code."""
    db = get_database()
    return db.get_description(code)
