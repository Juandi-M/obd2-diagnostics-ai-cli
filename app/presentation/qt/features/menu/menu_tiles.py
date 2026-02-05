from __future__ import annotations

from typing import Dict, List

TILE_ICONS: Dict[str, str] = {
    "diagnose": "🧪",
    "live": "📈",
    "ai": "✨",
    "reports": "🗂️",
    "settings": "⚙️",
    "uds": "🛠️",
    "module_map": "🗺️",
}

TILES: List[dict] = [
    {
        "label_key": "ai_scan",
        "color": "#d0d4dc",
        "nav_key": "ai",
        "icon_key": "ai",
        "full_width": True,
        "min_height": 160,
    },
    {"label_key": "diagnose", "color": "#c6d0da", "nav_key": "diagnose", "icon_key": "diagnose"},
    {"label_key": "live", "color": "#c6d6cc", "nav_key": "live", "icon_key": "live"},
    {"label_key": "reports", "color": "#d3c8bb", "nav_key": "reports", "icon_key": "reports"},
    {"label_key": "settings", "color": "#d8c7a3", "nav_key": "settings", "icon_key": "settings"},
    {"label_key": "uds_tools", "color": "#d0b7ad", "nav_key": "uds", "icon_key": "uds"},
    {"label_key": "module_map", "color": "#c9ced9", "nav_key": "module_map", "icon_key": "module_map"},
]

