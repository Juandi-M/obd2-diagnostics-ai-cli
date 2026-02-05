from __future__ import annotations

from typing import Callable, Dict

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.application.state import AppState
from app.presentation.qt.app_vm import get_vm
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.style import PAGE_MAX_WIDTH, panel_layout
from app.presentation.qt.widgets.status import add_status_badge


class SetupPage(QWidget):
    def __init__(self, state: AppState, on_continue: Callable[[], None]) -> None:
        super().__init__()
        self.state = state
        self.on_continue = on_continue
        self.brand_map: Dict[int, str] = {}

        layout = QVBoxLayout(self)
        title = QLabel(gui_t(self.state, "session_setup"))
        title.setObjectName("title")
        layout.addWidget(title)
        panel, panel_layout_ = panel_layout()
        panel.setMaximumWidth(PAGE_MAX_WIDTH)
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        form = QFormLayout()
        self.brand_combo = QComboBox()
        for opt_id, label, _, _, _ in get_vm().settings_vm.get_brand_options():
            idx = self.brand_combo.count()
            self.brand_combo.addItem(label, userData=opt_id)
            self.brand_map[idx] = opt_id
        self.brand_combo.currentIndexChanged.connect(self._brand_changed)
        self.vehicle_library_label = QLabel(gui_t(self.state, "vehicle_library"))
        form.addRow(self.vehicle_library_label, self.brand_combo)

        self.make = QLineEdit()
        self.model = QLineEdit()
        self.year = QLineEdit()
        self.trim = QLineEdit()

        self.make_label = QLabel(gui_t(self.state, "make"))
        self.model_label = QLabel(gui_t(self.state, "model"))
        self.year_label = QLabel(gui_t(self.state, "year"))
        self.trim_label = QLabel(gui_t(self.state, "trim"))
        form.addRow(self.make_label, self.make)
        form.addRow(self.model_label, self.model)
        form.addRow(self.year_label, self.year)
        form.addRow(self.trim_label, self.trim)
        panel_layout_.addLayout(form)

        btn_row = QHBoxLayout()
        save_btn = QPushButton(gui_t(self.state, "continue"))
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save)
        btn_row.addStretch(1)
        btn_row.addWidget(save_btn)
        panel_layout_.addLayout(btn_row)
        layout.addWidget(panel)

        self.status_badge = add_status_badge(layout, self.state)
        self.title = title
        self.save_btn = save_btn
        self._load_from_state()
        self._apply_brand_lock()

    def _brand_changed(self) -> None:
        brand_id = self.brand_combo.currentData()
        if brand_id is None:
            return
        get_vm().settings_vm.apply_brand_selection(str(brand_id))
        self._load_from_state()
        self._apply_brand_lock()

    def _load_from_state(self) -> None:
        profile = self.state.vehicle_profile or {}
        if self.state.brand_id is not None:
            for i in range(self.brand_combo.count()):
                if str(self.brand_combo.itemData(i)) == str(self.state.brand_id):
                    self.brand_combo.setCurrentIndex(i)
                    break
        self.make.setText(profile.get("make") or "")
        self.model.setText(profile.get("model") or "")
        self.year.setText(profile.get("year") or "")
        self.trim.setText(profile.get("trim") or "")

    def _save(self) -> None:
        if self.state.vehicle_group != "generic":
            self.state.vehicle_profile = {
                "make": self.make.text().strip() or None,
                "model": self.model.text().strip() or None,
                "year": self.year.text().strip() or None,
                "trim": self.trim.text().strip() or None,
                "source": "manual",
            }
            get_vm().settings_vm.save_profile_for_group()
        get_vm().settings_vm.save()
        self.on_continue()

    def refresh_text(self) -> None:
        self.title.setText(gui_t(self.state, "session_setup"))
        self.vehicle_library_label.setText(gui_t(self.state, "vehicle_library"))
        self.make_label.setText(gui_t(self.state, "make"))
        self.model_label.setText(gui_t(self.state, "model"))
        self.year_label.setText(gui_t(self.state, "year"))
        self.trim_label.setText(gui_t(self.state, "trim"))
        self.save_btn.setText(gui_t(self.state, "continue"))

    def _apply_brand_lock(self) -> None:
        # If brand implies make (e.g., Land Rover/Jaguar), lock Make field to avoid duplicate input.
        implied_make = None
        if self.state.brand_id in {"1", "2"}:
            implied_make = "Land Rover" if self.state.brand_id == "1" else "Jaguar"
        elif self.state.brand_id in {"3", "4", "5", "6"}:
            implied_make = {
                "3": "Jeep",
                "4": "Dodge",
                "5": "Chrysler",
                "6": "Ram",
            }.get(self.state.brand_id)

        if implied_make:
            self.make.setText(implied_make)
            self.make.setEnabled(False)
        else:
            self.make.setEnabled(True)

