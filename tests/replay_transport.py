from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, List, Optional, Tuple

from obd.elm.elm327 import ELM327
from obd.obd2.scanner import OBDScanner


def _normalize_command(command: str) -> str:
    return "".join(command.strip().split()).upper()


class ReplayMismatchError(AssertionError):
    pass


class ReplaySerial:
    def __init__(self, steps: Iterable[Dict[str, Any]]) -> None:
        self._steps: Deque[Dict[str, Any]] = deque(steps)
        self._buffer = bytearray()
        self.is_open = True
        self._pending_error: Optional[str] = None

    @property
    def in_waiting(self) -> int:
        if self._pending_error:
            error = self._pending_error
            self._pending_error = None
            if error in {"disconnect", "disconnected"}:
                self.is_open = False
                raise OSError("Device disconnected (replay)")
            if error in {"timeout", "communication"}:
                raise TimeoutError("Timeout (replay)")
        return len(self._buffer)

    def reset_input_buffer(self) -> None:
        self._buffer.clear()

    def reset_output_buffer(self) -> None:
        return None

    def flush(self) -> None:
        return None

    def close(self) -> None:
        self.is_open = False

    def write(self, data: bytes) -> int:
        command = data.decode("ascii", errors="ignore").replace("\r", "").replace("\n", "")
        if not command:
            return len(data)
        if not self._steps:
            raise ReplayMismatchError(f"No replay steps left for command {command!r}")

        step = self._steps.popleft()
        error = str(step.get("error", "")).lower().strip()
        if error:
            self._pending_error = error
            return len(data)

        expected = _normalize_command(str(step.get("command", "")))
        actual = _normalize_command(command)
        if expected != actual:
            raise ReplayMismatchError(f"Replay mismatch: expected {step.get('command')!r}, got {command!r}")

        lines = step.get("lines") or []
        payload = "\r".join(str(line) for line in lines) + "\r>"
        self._buffer.extend(payload.encode("ascii", errors="ignore"))
        return len(data)

    def read(self, size: int = 1) -> bytes:
        if size <= 0:
            return b""
        if not self._buffer:
            return b""
        chunk = self._buffer[:size]
        del self._buffer[:size]
        return bytes(chunk)


@dataclass
class ReplayFixture:
    steps: List[Dict[str, Any]]
    meta: Dict[str, Any]
    expected: Dict[str, Any]


def load_fixture(path: Path) -> ReplayFixture:
    payload = json.loads(path.read_text(encoding="utf-8"))
    steps = payload.get("steps") or []
    meta = payload.get("meta") or {}
    expected = payload.get("expected") or {}
    return ReplayFixture(steps=steps, meta=meta, expected=expected)


def build_replay_scanner(fixture: ReplayFixture) -> Tuple[OBDScanner, ELM327]:
    elm = ELM327(port="REPLAY")
    elm.connection = ReplaySerial(fixture.steps)
    elm._is_connected = True  # pylint: disable=protected-access

    headers_on = bool(fixture.meta.get("headers_on", True))
    elm.headers_on = headers_on
    if fixture.meta.get("elm_version"):
        elm.elm_version = str(fixture.meta["elm_version"])
    if fixture.meta.get("protocol"):
        elm.protocol = str(fixture.meta["protocol"])

    scanner = OBDScanner(manufacturer=fixture.meta.get("manufacturer"))
    scanner.elm = elm
    scanner._connected = True  # pylint: disable=protected-access
    return scanner, elm
