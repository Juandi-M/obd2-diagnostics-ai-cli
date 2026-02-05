from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy,
    QVBoxLayout,
    QPushButton,
)

from app.presentation.qt.style import PAGE_MAX_WIDTH

TileSpec = Dict[str, Any]
TileButton = Tuple[QPushButton, TileSpec]


class MenuResponsiveLayout:
    """Small helper to keep MainMenuPage focused on UI wiring.

    Handles:
    - Responsive tile grid columns + density
    - Centering panels on wide windows (side spacers) vs full-width on narrow
    """

    def __init__(
        self,
        *,
        grid: QGridLayout,
        tile_buttons: List[TileButton],
        tiles_panel: QFrame,
        tiles_layout: QVBoxLayout,
        connect_panel: QFrame,
        connect_wrap: QHBoxLayout,
        tiles_wrap: QHBoxLayout,
        connect_left_spacer: QSpacerItem,
        connect_right_spacer: QSpacerItem,
        tiles_left_spacer: QSpacerItem,
        tiles_right_spacer: QSpacerItem,
    ) -> None:
        self.grid = grid
        self.tile_buttons = tile_buttons
        self.tiles_panel = tiles_panel
        self.tiles_layout = tiles_layout
        self.connect_panel = connect_panel
        self.connect_wrap = connect_wrap
        self.tiles_wrap = tiles_wrap
        self.connect_left_spacer = connect_left_spacer
        self.connect_right_spacer = connect_right_spacer
        self.tiles_left_spacer = tiles_left_spacer
        self.tiles_right_spacer = tiles_right_spacer
        self._current_columns = 0
        self._wrap_wide: Optional[bool] = None

    def update(self, width: int, height: int) -> None:
        columns = self._columns_for_width(width)
        if columns != self._current_columns:
            self._rebuild_grid(columns, height=height)
        else:
            self._apply_tile_density(columns, height=height)
        self._update_wrap_stretch(width)

    def _columns_for_width(self, width: int) -> int:
        if width >= 980:
            return 3
        if width >= 640:
            return 2
        return 1

    def _rebuild_grid(self, columns: int, *, height: int) -> None:
        if columns < 1:
            columns = 1
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().setParent(self.tiles_panel)
        self._apply_tile_density(columns, height=height)

        row = 0
        col = 0
        max_row = 0
        for btn, spec in self.tile_buttons:
            if spec.get("full_width"):
                if col != 0:
                    row += 1
                    col = 0
                self.grid.addWidget(btn, row, 0, 1, columns)
                max_row = max(max_row, row)
                row += 1
                col = 0
                continue
            self.grid.addWidget(btn, row, col, 1, 1)
            max_row = max(max_row, row)
            col += 1
            if col >= columns:
                row += 1
                col = 0
        for c in range(columns):
            self.grid.setColumnStretch(c, 1)
        for r in range(max_row + 1):
            self.grid.setRowStretch(r, 1)
        self._current_columns = columns

    def _apply_tile_density(self, columns: int, *, height: int) -> None:
        if columns >= 3:
            spacing, padding, density = 14, 16, ""
            tile_height, hero_height = 140, 160
        elif columns == 2:
            spacing, padding, density = 12, 14, "compact"
            tile_height, hero_height = 120, 140
        else:
            spacing, padding, density = 10, 12, "dense"
            tile_height, hero_height = 110, 130
        if height < 700:
            spacing = max(8, spacing - 2)
            padding = max(10, padding - 2)
            tile_height = max(96, tile_height - 14)
            hero_height = max(110, hero_height - 20)
            density = "dense" if density == "compact" else density or "compact"

        self.grid.setSpacing(spacing)
        self.tiles_layout.setContentsMargins(padding, padding, padding, padding)
        for btn, spec in self.tile_buttons:
            btn.setMinimumHeight(hero_height if spec.get("full_width") else tile_height)
            btn.setProperty("tileDensity", density)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def _update_wrap_stretch(self, width: int) -> None:
        wide = width >= 980
        if self._wrap_wide == wide:
            return
        if wide:
            self.connect_left_spacer.changeSize(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
            self.connect_right_spacer.changeSize(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
            self.tiles_left_spacer.changeSize(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
            self.tiles_right_spacer.changeSize(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
            self.connect_panel.setMaximumWidth(PAGE_MAX_WIDTH)
            self.tiles_panel.setMaximumWidth(PAGE_MAX_WIDTH)
        else:
            self.connect_left_spacer.changeSize(0, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
            self.connect_right_spacer.changeSize(0, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
            self.tiles_left_spacer.changeSize(0, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
            self.tiles_right_spacer.changeSize(0, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
            self.connect_panel.setMaximumWidth(16777215)
            self.tiles_panel.setMaximumWidth(16777215)
        # Force relayout when the spacer policies change.
        self.connect_wrap.invalidate()
        self.tiles_wrap.invalidate()
        self._wrap_wide = wide
