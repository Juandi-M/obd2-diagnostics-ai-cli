from __future__ import annotations

from typing import Any, Callable, Dict, List

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


def module_key(mod: Dict[str, Any]) -> str:
    return f"{mod.get('tx_id')}->{mod.get('rx_id')}"


def build_module_card(
    mod: Dict[str, Any],
    *,
    favorite: bool,
    on_toggle_favorite: Callable[[Dict[str, Any], QPushButton], None],
) -> QWidget:
    card = QFrame()
    card.setObjectName("card")
    card_layout = QHBoxLayout(card)
    # Give cards more breathing room; the module list can feel cramped otherwise.
    card_layout.setContentsMargins(14, 14, 14, 14)
    card_layout.setSpacing(12)
    card.setMinimumHeight(104)

    left = QVBoxLayout()
    left.setSpacing(4)
    tx = mod.get("tx_id") or "--"
    rx = mod.get("rx_id") or "--"
    mtype = mod.get("module_type") or "Unknown"
    title = QLabel(f"{tx} → {rx}")
    title.setObjectName("sectionTitle")
    subtitle = QLabel(mtype)
    subtitle.setObjectName("hint")
    left.addWidget(title)
    left.addWidget(subtitle)
    left.addStretch(1)

    tags_row = QHBoxLayout()
    tags_row.setSpacing(6)
    tags: List[str] = []
    addressing = mod.get("addressing")
    if addressing:
        tags.append(str(addressing))
    if mod.get("protocol"):
        tags.append(f"CAN {mod.get('protocol')}")
    if mod.get("requires_security"):
        tags.append("Security")
    if (mod.get("fingerprint") or {}).get("vin"):
        tags.append("VIN")
    for tag in tags:
        lbl = QLabel(tag)
        lbl.setObjectName("tag")
        tags_row.addWidget(lbl)
    left.addLayout(tags_row)

    card_layout.addLayout(left)
    card_layout.addStretch(1)

    fav_btn = QPushButton("★" if favorite else "☆")
    fav_btn.setObjectName("secondary")
    fav_btn.setFixedWidth(44)
    fav_btn.clicked.connect(lambda _=False, m=mod, b=fav_btn: on_toggle_favorite(m, b))
    card_layout.addWidget(fav_btn)
    return card
