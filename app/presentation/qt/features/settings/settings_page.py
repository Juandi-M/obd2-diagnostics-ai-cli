from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.application.state import AppState
from app.presentation.qt.app_vm import get_vm
from app.presentation.qt.dialogs.message_box import ui_info
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.style import panel_layout
from app.presentation.qt.widgets.scroll import VerticalScrollArea


class SettingsPage(QWidget):
    def __init__(self, state: AppState, on_back: Callable[[], None], on_reconnect: Callable[[], None]) -> None:
        super().__init__()
        self.state = state
        self.on_back = on_back
        self.on_reconnect = on_reconnect
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

        title = QLabel(gui_t(self.state, "settings_title"))
        title.setObjectName("title")
        content_layout.addWidget(title)

        self.language_combo = QComboBox()
        self.language_combo.setObjectName("langSelect")
        self.language_combo.addItem("🇺🇸 English", userData="en")
        self.language_combo.addItem("🇪🇸 Español", userData="es")
        if str(self.state.language).lower().startswith("es"):
            self.language_combo.setCurrentIndex(1)

        self.brand_combo = QComboBox()
        for opt_id, label, _, _, _ in get_vm().settings_vm.get_brand_options():
            self.brand_combo.addItem(label, userData=opt_id)
        if self.state.brand_id is not None:
            for i in range(self.brand_combo.count()):
                if str(self.brand_combo.itemData(i)) == str(self.state.brand_id):
                    self.brand_combo.setCurrentIndex(i)
                    break
        self.brand_combo.currentIndexChanged.connect(self._on_brand_change)

        self.make = QLineEdit()
        self.model = QLineEdit()
        self.year = QLineEdit()
        self.trim = QLineEdit()
        profile = self.state.vehicle_profile or {}
        self.make.setText(profile.get("make") or "")
        self.model.setText(profile.get("model") or "")
        self.year.setText(profile.get("year") or "")
        self.trim.setText(profile.get("trim") or "")

        self.log_format = QComboBox()
        self.log_format.addItems(["csv", "json"])
        self.log_format.setCurrentText(self.state.log_format)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 10)
        self.interval_spin.setValue(int(self.state.monitor_interval))
        self.verbose_check = QCheckBox(gui_t(self.state, "verbose"))
        self.verbose_check.setChecked(self.state.verbose)

        self.language_label = QLabel(gui_t(self.state, "language"))
        self.vehicle_library_label = QLabel(gui_t(self.state, "vehicle_library"))
        self.log_format_label = QLabel(gui_t(self.state, "log_format"))
        self.monitor_label = QLabel(gui_t(self.state, "monitor_interval"))
        self.make_label = QLabel(gui_t(self.state, "make"))
        self.model_label = QLabel(gui_t(self.state, "model"))
        self.year_label = QLabel(gui_t(self.state, "year"))
        self.trim_label = QLabel(gui_t(self.state, "trim"))

        general_panel, general_layout = panel_layout(padding=16)
        self.general_title = QLabel(gui_t(self.state, "general"))
        self.general_title.setObjectName("sectionTitle")
        general_layout.addWidget(self.general_title)
        general_form = QFormLayout()
        general_form.addRow(self.language_label, self.language_combo)
        general_layout.addLayout(general_form)

        vehicle_panel, vehicle_layout = panel_layout(padding=16)
        self.vehicle_title = QLabel(gui_t(self.state, "vehicle_section"))
        self.vehicle_title.setObjectName("sectionTitle")
        vehicle_layout.addWidget(self.vehicle_title)
        vehicle_form = QFormLayout()
        vehicle_form.addRow(self.vehicle_library_label, self.brand_combo)
        vehicle_form.addRow(self.make_label, self.make)
        vehicle_form.addRow(self.model_label, self.model)
        vehicle_form.addRow(self.year_label, self.year)
        vehicle_form.addRow(self.trim_label, self.trim)
        vehicle_layout.addLayout(vehicle_form)

        logging_panel, logging_layout = panel_layout(padding=16)
        self.logging_title = QLabel(gui_t(self.state, "logging"))
        self.logging_title.setObjectName("sectionTitle")
        logging_layout.addWidget(self.logging_title)
        logging_form = QFormLayout()
        logging_form.addRow(self.log_format_label, self.log_format)
        logging_form.addRow(self.monitor_label, self.interval_spin)
        logging_form.addRow("", self.verbose_check)
        logging_layout.addLayout(logging_form)

        grid = QGridLayout()
        grid.setSpacing(14)
        grid.addWidget(general_panel, 0, 0)
        grid.addWidget(vehicle_panel, 0, 1)
        grid.addWidget(logging_panel, 1, 0, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        content_layout.addLayout(grid)

        btn_row = QHBoxLayout()
        save_btn = QPushButton(gui_t(self.state, "save"))
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save)
        reconnect_btn = QPushButton(gui_t(self.state, "reconnect"))
        reconnect_btn.setObjectName("secondary")
        reconnect_btn.clicked.connect(self.on_reconnect)
        back_btn = QPushButton(gui_t(self.state, "back"))
        back_btn.setObjectName("secondary")
        back_btn.clicked.connect(self.on_back)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(reconnect_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(back_btn)
        content_layout.addLayout(btn_row)
        content_layout.addStretch(1)

        self.title = title
        self.save_btn = save_btn
        self.reconnect_btn = reconnect_btn
        self.back_btn = back_btn
        self._apply_brand_lock()

    def refresh_text(self) -> None:
        self.title.setText(gui_t(self.state, "settings_title"))
        self.general_title.setText(gui_t(self.state, "general"))
        self.vehicle_title.setText(gui_t(self.state, "vehicle_section"))
        self.logging_title.setText(gui_t(self.state, "logging"))
        self.language_label.setText(gui_t(self.state, "language"))
        self.vehicle_library_label.setText(gui_t(self.state, "vehicle_library"))
        self.make_label.setText(gui_t(self.state, "make"))
        self.model_label.setText(gui_t(self.state, "model"))
        self.year_label.setText(gui_t(self.state, "year"))
        self.trim_label.setText(gui_t(self.state, "trim"))
        self.log_format_label.setText(gui_t(self.state, "log_format"))
        self.monitor_label.setText(gui_t(self.state, "monitor_interval"))
        self.verbose_check.setText(gui_t(self.state, "verbose"))
        self.save_btn.setText(gui_t(self.state, "save"))
        self.reconnect_btn.setText(gui_t(self.state, "reconnect"))
        self.back_btn.setText(gui_t(self.state, "back"))

    def _save(self) -> None:
        lang_code = self.language_combo.currentData()
        if isinstance(lang_code, str):
            self.state.language = lang_code
        brand_id = self.brand_combo.currentData()
        if isinstance(brand_id, str):
            get_vm().settings_vm.apply_brand_selection(brand_id)
        self.state.vehicle_profile = {
            "make": self.make.text().strip() or None,
            "model": self.model.text().strip() or None,
            "year": self.year.text().strip() or None,
            "trim": self.trim.text().strip() or None,
            "source": "manual",
        }
        get_vm().settings_vm.save_profile_for_group()
        self.state.log_format = self.log_format.currentText()
        self.state.monitor_interval = float(self.interval_spin.value())
        self.state.set_verbose(self.verbose_check.isChecked())
        get_vm().settings_vm.save()
        window = self.window()
        if hasattr(window, "_refresh_status_badges"):
            window._refresh_status_badges()
        if hasattr(window, "show_toast"):
            window.show_toast("Settings saved.")
        else:
            ui_info(self, "Settings", "Settings saved.")

    def _apply_brand_lock(self) -> None:
        implied_make = None
        if self.state.brand_id in {"1", "2"}:
            implied_make = "Land Rover" if self.state.brand_id == "1" else "Jaguar"
        elif self.state.brand_id in {"3", "4", "5", "6"}:
            implied_make = {"3": "Jeep", "4": "Dodge", "5": "Chrysler", "6": "Ram"}.get(self.state.brand_id)

        if implied_make:
            self.make.setText(implied_make)
            self.make.setEnabled(False)
        else:
            self.make.setEnabled(True)

    def _on_brand_change(self) -> None:
        brand_id = self.brand_combo.currentData()
        if isinstance(brand_id, str):
            get_vm().settings_vm.apply_brand_selection(brand_id)
        self._apply_brand_lock()
