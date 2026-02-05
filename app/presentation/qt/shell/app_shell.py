from __future__ import annotations

import time
from typing import Callable, Dict

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.application.state import AppState
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.widgets.scroll import VerticalScrollArea


class AppShell(QWidget):
    def __init__(self, state: AppState, on_nav: Callable[[str], None]) -> None:
        super().__init__()
        self.state = state
        self.on_nav = on_nav
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(200)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(16, 20, 16, 20)
        side_layout.setSpacing(8)

        title = QLabel(gui_t(self.state, "app_title"))
        title.setObjectName("sidebarTitle")
        side_layout.addWidget(title)

        toggle_btn = QPushButton("◀")
        toggle_btn.setObjectName("secondary")
        toggle_btn.clicked.connect(self._toggle_sidebar)
        side_layout.addWidget(toggle_btn)

        self.nav_buttons: Dict[str, QPushButton] = {}
        self.nav_icons = {
            "menu": "🏠",
            "diagnose": "🧪",
            "live": "📈",
            "ai": "✨",
            "uds": "🛠️",
            "module_map": "🗺️",
            "reports": "🗂️",
            "settings": "⚙️",
        }
        nav_items = [
            ("menu", gui_t(self.state, "main_menu")),
            ("diagnose", gui_t(self.state, "diagnose")),
            ("live", gui_t(self.state, "live")),
            ("ai", gui_t(self.state, "ai_report")),
            ("uds", gui_t(self.state, "uds_tools")),
            ("module_map", gui_t(self.state, "module_map")),
            ("reports", gui_t(self.state, "reports")),
            ("settings", gui_t(self.state, "settings")),
        ]
        for key, label in nav_items:
            icon = self.nav_icons.get(key, "")
            btn = QPushButton(f"{icon} {label}".strip())
            btn.setObjectName("navButton")
            btn.clicked.connect(lambda _=False, k=key: self.on_nav(k))
            self.nav_buttons[key] = btn
            side_layout.addWidget(btn)

        side_layout.addStretch(1)
        layout.addWidget(self.sidebar)

        self.content = QFrame()
        self.content.setObjectName("contentArea")
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(24, 16, 24, 20)
        content_layout.setSpacing(12)

        self.connection_bar = QFrame()
        self.connection_bar.setObjectName("card")
        bar_layout = QHBoxLayout(self.connection_bar)
        bar_layout.setContentsMargins(12, 8, 12, 8)
        self.conn_label = QLabel("")
        self.conn_label.setObjectName("sectionTitle")
        self.last_seen_label = QLabel("")
        self.last_seen_label.setObjectName("hint")
        self.signal_label = QLabel("")
        self.signal_label.setObjectName("hint")
        self.reconnect_btn = QPushButton(gui_t(self.state, "reconnect"))
        self.reconnect_btn.setObjectName("secondary")
        bar_layout.addWidget(self.conn_label)
        bar_layout.addStretch(1)
        bar_layout.addWidget(self.last_seen_label)
        bar_layout.addWidget(self.signal_label)
        bar_layout.addWidget(self.reconnect_btn)
        content_layout.addWidget(self.connection_bar)

        self.content_layout = content_layout
        layout.addWidget(self.content)
        self._collapsed = False
        self.toggle_btn = toggle_btn

    def set_page(self, widget: QWidget) -> None:
        # Replace current content with provided widget.
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                w = item.widget()
                if isinstance(w, QScrollArea) and w.widget():
                    w.widget().setParent(None)
                w.setParent(None)
        self.content_layout.addWidget(self.connection_bar)
        page_widget = widget
        if not isinstance(widget, QScrollArea) and not getattr(widget, "_uses_internal_scroll", False):
            scroll = VerticalScrollArea()
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            scroll.setWidget(widget)
            page_widget = scroll
        self.content_layout.addWidget(page_widget)

    def set_nav_enabled(self, enabled: bool) -> None:
        for btn in self.nav_buttons.values():
            btn.setEnabled(enabled)

    def set_active(self, key: str) -> None:
        for k, btn in self.nav_buttons.items():
            btn.setProperty("active", "true" if k == key else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def refresh_text(self) -> None:
        # Update nav labels after language change.
        labels = {
            "menu": gui_t(self.state, "main_menu"),
            "diagnose": gui_t(self.state, "diagnose"),
            "live": gui_t(self.state, "live"),
            "ai": gui_t(self.state, "ai_report"),
            "uds": gui_t(self.state, "uds_tools"),
            "module_map": gui_t(self.state, "module_map"),
            "reports": gui_t(self.state, "reports"),
            "settings": gui_t(self.state, "settings"),
        }
        for key, label in labels.items():
            if key in self.nav_buttons:
                icon = self.nav_icons.get(key, "")
                self.nav_buttons[key].setText(f"{icon} {label}".strip())
        self.reconnect_btn.setText(gui_t(self.state, "reconnect"))

    def _toggle_sidebar(self) -> None:
        self._collapsed = not self._collapsed
        if self._collapsed:
            self.sidebar.setFixedWidth(64)
            self.toggle_btn.setText("▶")
            for btn in self.nav_buttons.values():
                btn.setText("")
            self.toggle_btn.setToolTip("Expand")
        else:
            self.sidebar.setFixedWidth(200)
            self.toggle_btn.setText("◀")
            self.refresh_text()
            self.toggle_btn.setToolTip("Collapse")

    def update_connection_bar(self) -> None:
        connected = self.state.active_scanner() is not None
        status = gui_t(self.state, "connected") if connected else gui_t(self.state, "disconnected")
        vin_value = self.state.last_vin or ""
        vin_label = f" | {gui_t(self.state, 'vin_label')}: {vin_value}" if vin_value else ""
        self.conn_label.setText(f"{gui_t(self.state, 'status')}: {status}{vin_label}")
        if self.state.last_seen_at:
            delta = int(time.time() - self.state.last_seen_at)
            if delta < 60:
                seen = f"{delta}s ago"
            elif delta < 3600:
                seen = f"{delta // 60}m ago"
            else:
                seen = f"{delta // 3600}h ago"
            device = self.state.last_seen_device or "device"
            self.last_seen_label.setText(f"Last seen ({device}): {seen}")
        else:
            self.last_seen_label.setText("Last seen: —")
        if isinstance(self.state.last_seen_rssi, int) and self.state.last_seen_rssi > -999:
            self.signal_label.setText(f"Signal: {self.state.last_seen_rssi} dBm")
        else:
            self.signal_label.setText("Signal: —")

