from __future__ import annotations

from typing import Dict, List, Tuple

# (pid, label, unit, min, max)
ALL_METRICS: List[Tuple[str, str, str, float, float]] = [
    ("05", "Coolant Temp", "°C", 0, 130),
    ("0C", "RPM", "rpm", 0, 6000),
    ("0D", "Speed", "km/h", 0, 200),
    ("11", "Throttle", "%", 0, 100),
    ("49", "Pedal", "%", 0, 100),
    ("42", "Voltage", "V", 0, 16),
]

METRIC_ICONS: Dict[str, str] = {
    "05": "🌡️",
    "0C": "🧭",
    "0D": "🚗",
    "11": "⚙️",
    "49": "🦶",
    "42": "🔋",
}

