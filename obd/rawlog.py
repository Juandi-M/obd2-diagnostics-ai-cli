import time
from pathlib import Path
from typing import List, Optional

from app.infrastructure.persistence.data_paths import logs_dir

class RawLogger:
    def __init__(self, path: Optional[str] = None):
        default_path = logs_dir() / "obd_raw.log"
        self.path = Path(path) if path else default_path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, direction: str, command: str, lines: List[str]):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {direction} {command}\n")
            for ln in lines:
                f.write(f"  {ln}\n")
