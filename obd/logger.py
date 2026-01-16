"""
Session Logger Module
=====================
Handles logging of OBD sessions to CSV and JSON files.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from .utils import cr_now, cr_timestamp, cr_timestamp_filename


class SessionLogger:
    """
    Logs OBD monitoring sessions to CSV or JSON files.
    
    Usage:
        logger = SessionLogger("logs/")
        logger.start_session(format="csv")
        
        while monitoring:
            readings = scanner.read_live_data()
            logger.log_readings(readings)
        
        logger.end_session()
    """
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_file: Optional[Path] = None
        self.session_format: str = "csv"
        self.session_start = None
        self.reading_count: int = 0
        self._csv_writer = None
        self._file_handle = None
        self._json_data: List[Dict] = []
        self._headers_written: bool = False
        self._csv_fieldnames: List[str] = []
    
    def start_session(self, format: str = "csv", filename: Optional[str] = None) -> Path:
        """
        Start a new logging session.
        
        Args:
            format: "csv" or "json"
            filename: Optional custom filename (without extension)
            
        Returns:
            Path to the session file
        """
        self.session_format = format.lower()
        self.session_start = cr_now()
        self.reading_count = 0
        self._headers_written = False
        self._json_data = []
        self._csv_fieldnames = []
        
        # Generate filename
        if filename:
            base_name = filename
        else:
            base_name = f"session_{cr_timestamp_filename()}"
        
        ext = ".csv" if self.session_format == "csv" else ".json"
        self.session_file = self.log_dir / f"{base_name}{ext}"
        
        # Open file for CSV (JSON writes at end)
        if self.session_format == "csv":
            self._file_handle = open(self.session_file, "w", newline="", encoding="utf-8")
        
        return self.session_file
    
    def log_readings(self, readings: Dict[str, Any]) -> None:
        """
        Log a set of sensor readings.
        
        Args:
            readings: Dictionary of PID -> SensorReading from scanner.read_live_data()
        """
        if not self.session_file:
            raise RuntimeError("No active session. Call start_session() first.")
        
        timestamp = cr_timestamp()
        
        # Flatten readings to simple dict
        row = {"timestamp": timestamp}
        
        for pid, reading in readings.items():
            col_name = self._pid_to_column(reading.name)
            row[col_name] = reading.value
            row[f"{col_name}_unit"] = reading.unit
        
        if self.session_format == "csv":
            self._write_csv_row(row)
        else:
            self._json_data.append(row)
        
        self.reading_count += 1
    
    def log_dtcs(self, dtcs: List[Any]) -> None:
        """Log diagnostic trouble codes to the session."""
        if not self.session_file:
            raise RuntimeError("No active session. Call start_session() first.")
        
        timestamp = cr_timestamp()
        
        for dtc in dtcs:
            row = {
                "timestamp": timestamp,
                "type": "DTC",
                "code": dtc.code,
                "description": dtc.description,
                "status": dtc.status,
            }
            
            if self.session_format == "csv":
                self._write_csv_row(row)
            else:
                self._json_data.append(row)
    
    def log_freeze_frame(self, freeze_data: Dict[str, Any]) -> None:
        """Log freeze frame data."""
        if not self.session_file:
            raise RuntimeError("No active session. Call start_session() first.")
        
        timestamp = cr_timestamp()
        row = {"timestamp": timestamp, "type": "FREEZE_FRAME", **freeze_data}
        
        if self.session_format == "csv":
            self._write_csv_row(row)
        else:
            self._json_data.append(row)
    
    def log_event(self, event_type: str, message: str, data: Optional[Dict] = None) -> None:
        """
        Log a custom event (warnings, errors, notes).
        
        Args:
            event_type: Type of event (e.g., "WARNING", "ERROR", "NOTE")
            message: Event message
            data: Optional additional data
        """
        if not self.session_file:
            raise RuntimeError("No active session. Call start_session() first.")
        
        timestamp = cr_timestamp()
        row = {
            "timestamp": timestamp,
            "type": event_type,
            "message": message,
        }
        if data:
            row.update(data)
        
        if self.session_format == "csv":
            self._write_csv_row(row)
        else:
            self._json_data.append(row)
    
    def _pid_to_column(self, name: str) -> str:
        """Convert PID name to short column name."""
        mappings = {
            "Engine Coolant Temperature": "coolant",
            "Engine RPM": "rpm",
            "Vehicle Speed": "speed",
            "Throttle Position": "throttle",
            "Relative Throttle Position": "throttle_rel",
            "Accelerator Pedal Position D": "pedal_d",
            "Accelerator Pedal Position E": "pedal_e",
            "Control Module Voltage": "voltage",
            "Intake Manifold Pressure": "map",
            "Intake Air Temperature": "iat",
            "Short Term Fuel Trim - Bank 1": "stft_b1",
            "Long Term Fuel Trim - Bank 1": "ltft_b1",
            "Calculated Engine Load": "load",
            "Timing Advance": "timing",
            "MAF Air Flow Rate": "maf",
            "Fuel Tank Level": "fuel_level",
            "Commanded Throttle Actuator": "throttle_cmd",
        }
        return mappings.get(name, name.lower().replace(" ", "_")[:20])
    
    def _write_csv_row(self, row: Dict) -> None:
        """Write a row to CSV file."""
        if not self._file_handle:
            return
        
        if not self._headers_written:
            self._csv_fieldnames = list(row.keys())
            self._csv_writer = csv.DictWriter(
                self._file_handle, 
                fieldnames=self._csv_fieldnames,
                extrasaction="ignore"
            )
            self._csv_writer.writeheader()
            self._headers_written = True
        
        for key in row.keys():
            if key not in self._csv_fieldnames:
                self._csv_fieldnames.append(key)
        
        self._csv_writer.writerow(row)
        self._file_handle.flush()
    
    def end_session(self) -> Dict[str, Any]:
        """End the current logging session."""
        if not self.session_file:
            return {}
        
        session_end = cr_now()
        duration = (session_end - self.session_start).total_seconds() if self.session_start else 0
        
        summary = {
            "file": str(self.session_file),
            "format": self.session_format,
            "start_time": self.session_start.strftime("%Y-%m-%d %H:%M:%S") if self.session_start else None,
            "end_time": session_end.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_seconds": duration,
            "reading_count": self.reading_count,
        }
        
        # Write JSON file at end
        if self.session_format == "json":
            output = {
                "session": summary,
                "data": self._json_data,
            }
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
        
        # Close CSV file
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
        
        # Reset state
        self.session_file = None
        self._csv_writer = None
        self._json_data = []
        
        return summary
    
    @property
    def is_active(self) -> bool:
        """Check if a session is currently active."""
        return self.session_file is not None
    
    def list_sessions(self) -> List[Path]:
        """List all saved session files."""
        csv_files = list(self.log_dir.glob("*.csv"))
        json_files = list(self.log_dir.glob("*.json"))
        return sorted(csv_files + json_files, reverse=True)


class QuickLog:
    """
    Simple context manager for one-off logging.
    
    Usage:
        with QuickLog("logs/") as log:
            log.log_readings(readings)
    """
    
    def __init__(self, log_dir: str = "logs", format: str = "csv"):
        self.logger = SessionLogger(log_dir)
        self.format = format
    
    def __enter__(self) -> SessionLogger:
        self.logger.start_session(format=self.format)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.end_session()
