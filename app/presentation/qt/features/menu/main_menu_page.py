from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.application.state import AppState
from app.presentation.qt.features.menu.menu_responsive import MenuResponsiveLayout
from app.presentation.qt.features.menu.menu_tiles import TILE_ICONS, TILES
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.style import PAGE_MAX_WIDTH, apply_shadow, panel_layout
from app.presentation.qt.widgets.scroll import VerticalScrollArea


class MainMenuPage(QWidget):
    def __init__(
        self,
        state: AppState,
        on_select: Callable[[str], None],
        on_reconnect: Callable[[], None],
        *,
        on_language_change: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()
        self.state = state
        self.on_reconnect = on_reconnect
        self._on_language_change = on_language_change
        self._uses_internal_scroll = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scroll_area = VerticalScrollArea()
        layout.addWidget(self.scroll_area)

        content = QWidget()
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)
        self.scroll_area.setWidget(content)

        self.title = QLabel(gui_t(self.state, "main_menu"))
        self.title.setObjectName("title")
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(10)
        header_row.addWidget(self.title)
        header_row.addStretch(1)

        self.lang_label = QLabel(gui_t(self.state, "language"))
        self.lang_label.setObjectName("chip")
        self.lang_combo = QComboBox()
        self.lang_combo.setObjectName("langSelect")
        self.lang_combo.addItem("🇺🇸 English", userData="en")
        self.lang_combo.addItem("🇪🇸 Español", userData="es")
        self.lang_combo.currentIndexChanged.connect(self._set_language)
        header_row.addWidget(self.lang_label)
        header_row.addWidget(self.lang_combo)
        content_layout.addLayout(header_row)

        # Default language from state if set.
        if str(self.state.language).lower().startswith("es"):
            self.lang_combo.setCurrentIndex(1)

        connect_panel = QFrame()
        connect_panel.setObjectName("card")
        connect_panel.setMaximumWidth(PAGE_MAX_WIDTH)
        connect_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        apply_shadow(connect_panel, blur=16, y=6)
        connect_layout = QHBoxLayout(connect_panel)
        connect_layout.setContentsMargins(18, 16, 18, 16)
        self.connect_title = QLabel(gui_t(self.state, "device"))
        self.connect_title.setObjectName("sectionTitle")
        status = gui_t(self.state, "connected") if self.state.active_scanner() else gui_t(self.state, "disconnected")
        hint_text = gui_t(self.state, "ready_to_scan") if self.state.active_scanner() else gui_t(self.state, "connect_menu_hint")
        self.connect_hint = QLabel(f"{status} · {hint_text}")
        self.connect_hint.setObjectName("hint")
        left_col = QVBoxLayout()
        left_col.addWidget(self.connect_title)
        left_col.addWidget(self.connect_hint)
        left_col.addStretch(1)
        self.connect_btn = QPushButton(gui_t(self.state, "connect_device"))
        self.connect_btn.setObjectName("primary")
        self.connect_btn.setMinimumWidth(190)
        self.connect_btn.clicked.connect(self.on_reconnect)
        connect_layout.addLayout(left_col)
        connect_layout.addStretch(1)
        connect_layout.addWidget(self.connect_btn)
        connect_wrap = QHBoxLayout()
        connect_wrap.setContentsMargins(0, 0, 0, 0)
        connect_wrap.setSpacing(0)
        self.connect_left_spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.connect_right_spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        connect_wrap.addItem(self.connect_left_spacer)
        connect_wrap.addWidget(connect_panel, 6)
        connect_wrap.addItem(self.connect_right_spacer)
        content_layout.addLayout(connect_wrap)

        self.grid = QGridLayout()
        self.grid.setSpacing(14)

        self.tile_buttons: List[Tuple[QPushButton, Dict[str, Any]]] = []
        for spec in TILES:
            icon = TILE_ICONS.get(spec["icon_key"], "")
            btn = QPushButton(f"{icon} {gui_t(self.state, spec['label_key'])}".strip())
            btn.setObjectName("tile")
            btn.setStyleSheet(
                "QPushButton#tile {{ background-color: {0}; }} "
                "QPushButton#tile:hover {{ background-color: {0}; }} "
                "QPushButton#tile:pressed {{ background-color: {0}; }}"
                .format(spec["color"])
            )
            btn.setMinimumHeight(spec.get("min_height", 140))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.clicked.connect(lambda _=False, k=spec["nav_key"]: on_select(k))
            self.tile_buttons.append((btn, spec))

        tiles_panel, tiles_layout = panel_layout()
        tiles_panel.setMaximumWidth(PAGE_MAX_WIDTH)
        tiles_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tiles_layout.addLayout(self.grid)
        tiles_wrap = QHBoxLayout()
        tiles_wrap.setContentsMargins(0, 0, 0, 0)
        tiles_wrap.setSpacing(0)
        self.tiles_left_spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.tiles_right_spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        tiles_wrap.addItem(self.tiles_left_spacer)
        tiles_wrap.addWidget(tiles_panel, 6)
        tiles_wrap.addItem(self.tiles_right_spacer)
        content_layout.addLayout(tiles_wrap)
        content_layout.addStretch(1)

        self._responsive = MenuResponsiveLayout(
            grid=self.grid,
            tile_buttons=self.tile_buttons,
            tiles_panel=tiles_panel,
            tiles_layout=tiles_layout,
            connect_panel=connect_panel,
            connect_wrap=connect_wrap,
            tiles_wrap=tiles_wrap,
            connect_left_spacer=self.connect_left_spacer,
            connect_right_spacer=self.connect_right_spacer,
            tiles_left_spacer=self.tiles_left_spacer,
            tiles_right_spacer=self.tiles_right_spacer,
        )
        self._responsive.update(self.width(), self.height())

    def refresh_text(self) -> None:
        self.title.setText(gui_t(self.state, "main_menu"))
        self.lang_label.setText(gui_t(self.state, "language"))
        lang_idx = 1 if str(self.state.language).lower().startswith("es") else 0
        self.lang_combo.blockSignals(True)
        self.lang_combo.setCurrentIndex(lang_idx)
        self.lang_combo.blockSignals(False)

        for btn, spec in self.tile_buttons:
            icon = TILE_ICONS.get(spec["icon_key"], "")
            btn.setText(f"{icon} {gui_t(self.state, spec['label_key'])}".strip())
        self.connect_title.setText(gui_t(self.state, "device"))
        status = gui_t(self.state, "connected") if self.state.active_scanner() else gui_t(self.state, "disconnected")
        hint_text = gui_t(self.state, "ready_to_scan") if self.state.active_scanner() else gui_t(self.state, "connect_menu_hint")
        self.connect_hint.setText(f"{status} · {hint_text}")
        self.connect_btn.setText(gui_t(self.state, "connect_device"))

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 - Qt naming
        super().resizeEvent(event)
        if hasattr(self, "_responsive"):
            self._responsive.update(self.width(), self.height())

    def _set_language(self) -> None:
        code = self.lang_combo.currentData()
        if isinstance(code, str):
            self.state.language = code
        if self._on_language_change:
            self._on_language_change()

