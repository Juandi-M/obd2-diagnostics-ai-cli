from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

from obd.dtc import parse_dtc_response, lookup_code, get_database
from obd.pids.registry import get_pid_info
from obd.pids.decode import decode_pid_response

from obd.kline.session import KLineSession


@dataclass(frozen=True)
class KLineDTC:
    code: str
    description: str


@dataclass(frozen=True)
class KLineDTCReadResult:
    mode: str
    dtcs: List[KLineDTC]
    raw_hex: str


@dataclass(frozen=True)
class KLinePIDResult:
    pid: str
    name: str
    unit: str
    value: Optional[float]
    raw_hex: str


class KLineScanner:
    """
    Scanner “producto” sobre KLineSession.

    Reutiliza:
    - obd/dtc: parse_dtc_response + database lookup
    - obd/pids: registry + decode_pid_response

    Implementa:
    - read_dtcs (Mode 03/07/0A)
    - clear_dtcs (Mode 04)
    - read_pid (Mode 01)
    """

    def __init__(
        self,
        session: KLineSession,
        *,
        manufacturer: Optional[str] = None,
    ):
        self.session = session
        self.manufacturer = manufacturer

    # ---------- DTCs ----------

    def read_dtcs(self, mode: str = "03") -> KLineDTCReadResult:
        """
        Lee DTCs:
        - 03: stored
        - 07: pending
        - 0A: permanent
        """
        mode = (mode or "03").strip().upper()

        raw_hex = self.session.query_hex(mode)

        # Aseguramos que parse vea el prefijo correcto (43/47/4A)
        expected_prefix = {"03": "43", "07": "47", "0A": "4A"}.get(mode, "43")
        idx = raw_hex.find(expected_prefix)
        hex_for_parse = raw_hex[idx:] if idx >= 0 else raw_hex

        codes = parse_dtc_response(hex_for_parse, mode=mode)

        # DB lookup (usa manufacturer si se setea)
        if self.manufacturer:
            db = get_database(self.manufacturer)
            desc_fn = db.get_description
        else:
            desc_fn = lookup_code

        dtcs = [KLineDTC(code=c, description=desc_fn(c)) for c in codes]
        return KLineDTCReadResult(mode=mode, dtcs=dtcs, raw_hex=raw_hex)

    def clear_dtcs(self) -> Tuple[bool, str]:
        """
        Limpia DTCs (Mode 04).
        """
        lines = self.session.query_lines("04")
        up = " ".join(lines).upper()

        # Algunos ECUs responden "44" (respuesta a 04), otros solo "OK"
        hex_blob = "".join(ch for ch in up if ch in "0123456789ABCDEF")

        if "DISCONNECTED" in up:
            return False, "ELM disconnected"
        if "ERROR" in up:
            return False, f"ERROR: {lines[:3]}"
        if "NO DATA" in up:
            return False, "NO DATA"
        if "UNABLE TO CONNECT" in up:
            return False, "UNABLE TO CONNECT"

        if "44" in hex_blob or "OK" in up:
            return True, "OK"

        # Aceptación conservadora: si no hubo error textual, puede haber sido OK
        return True, f"OK?(weak): {lines[:3]}"

    # ---------- PIDs (Mode 01) ----------

    def read_pid(self, pid: str) -> KLinePIDResult:
        """
        Lee un PID Mode 01:
        - pid puede venir como "0C" o "010C"
        """
        p = (pid or "").strip().upper()
        if p.startswith("01") and len(p) == 4:
            p = p[2:]

        pid_info = get_pid_info(p)
        if not pid_info:
            # PID no registrado => devolvemos raw
            raw_hex = self.session.query_hex(f"01{p}")
            return KLinePIDResult(pid=p, name=f"PID {p}", unit="", value=None, raw_hex=raw_hex)

        cmd = f"01{p}"
        raw_hex = self.session.query_hex(cmd)

        # Buscar respuesta "41{PID}"
        marker = f"41{p}"
        idx = raw_hex.find(marker)
        if idx < 0:
            return KLinePIDResult(
                pid=p,
                name=pid_info.name,
                unit=pid_info.unit,
                value=None,
                raw_hex=raw_hex,
            )

        data_start = idx + len(marker)
        # bytes esperados => 2 hex chars por byte
        needed = pid_info.bytes * 2
        data_hex = raw_hex[data_start : data_start + needed]

        val = decode_pid_response(p, data_hex)
        return KLinePIDResult(
            pid=p,
            name=pid_info.name,
            unit=pid_info.unit,
            value=val,
            raw_hex=raw_hex,
        )

    def live_basic(self) -> Dict[str, KLinePIDResult]:
        """
        Live data mínimo que casi siempre sirve:
        - RPM (0C)
        - Coolant temp (05)
        - Vehicle speed (0D)
        - Intake air temp (0F)
        - Throttle position (11)
        - Control module voltage (42) (si existe)
        """
        pids = ["0C", "05", "0D", "0F", "11", "42"]
        out: Dict[str, KLinePIDResult] = {}
        for p in pids:
            out[p] = self.read_pid(p)
        return out
