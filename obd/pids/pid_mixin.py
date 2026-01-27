# obd/obd2/pid_mixin.py
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from ..pids.standard_mode01 import PIDS
from ..pids.decode import decode_pid_response
from ..pids.sets import DIAGNOSTIC_PIDS
from ..obd2.models import SensorReading


class PidMixin:
    """
    Mode 01 PID reads over the base OBD2 query engine.

    Expects parent class to implement:
      - _obd_query_payload(command: str, expected_prefix: List[str])
          -> Optional[tuple[str, List[str]]]
            where payload tokens look like: ["41", "<PID>", "<A>", "<B>", ...]
    """

    def read_pid(
        self,
        pid: str,
        *,
        round_to: int = 2,
        allow_empty: bool = False,
    ) -> Optional[SensorReading]:
        """
        Read a single PID (Mode 01).

        round_to:
          - number of decimal digits (default 2)
        allow_empty:
          - if True, returns SensorReading even if decoder returns None (value=None)
            (default False)
        """
        if pid is None:
            return None

        pid = pid.strip().upper()
        if not pid:
            return None

        # Normalize "0C" vs "C"
        if len(pid) == 1:
            pid = "0" + pid

        pid_info = PIDS.get(pid)
        if not pid_info:
            return None

        found = self._obd_query_payload(f"01{pid}", expected_prefix=["41", pid])
        if not found:
            return None

        ecu, payload = found
        if not payload or len(payload) < 3:
            return None

        # Defensive: ensure it actually matches what we expect
        # payload example: ["41", "0C", "1A", "F8"]
        if payload[0].upper() != "41" or payload[1].upper() != pid:
            return None

        data_tokens = payload[2:]
        data_hex = "".join(t.strip() for t in data_tokens if t and t.strip()).upper()

        value = decode_pid_response(pid, data_hex)

        if value is None and not allow_empty:
            return None

        # Some PIDs may decode to int; keep consistent float formatting
        if value is not None:
            try:
                value = round(float(value), round_to)
            except (ValueError, TypeError):
                if not allow_empty:
                    return None
                value = None

        # If your SensorReading model doesn't have ecu, delete ecu=ecu below.
        return SensorReading(
            name=pid_info.name,
            value=value,
            unit=pid_info.unit,
            pid=pid,
            raw_hex=data_hex,
            ecu=ecu,
        )

    def read_live_data(
        self,
        pids: Optional[Sequence[str]] = None,
        *,
        round_to: int = 2,
        dedupe: bool = True,
        stop_on_error: bool = False,
    ) -> Dict[str, SensorReading]:
        """
        Read a set of PIDs (Mode 01).

        dedupe:
          - remove repeated PIDs while keeping order

        stop_on_error:
          - if True, raises exceptions (useful in tests)
          - if False, continues scanning and skips failures
        """
        pid_list: Iterable[str] = pids if pids is not None else DIAGNOSTIC_PIDS

        # Dedupe while preserving order
        normalized: List[str] = []
        seen = set()

        for p in pid_list:
            if p is None:
                continue
            p = p.strip().upper()
            if not p:
                continue
            if len(p) == 1:
                p = "0" + p
            if dedupe:
                if p in seen:
                    continue
                seen.add(p)
            normalized.append(p)

        results: Dict[str, SensorReading] = {}

        for pid in normalized:
            try:
                reading = self.read_pid(pid, round_to=round_to)
                if reading:
                    results[pid] = reading
            except Exception:
                if stop_on_error:
                    raise
                # continue scanning even if one PID breaks
                continue

        return results


__all__ = ["PidMixin"]
