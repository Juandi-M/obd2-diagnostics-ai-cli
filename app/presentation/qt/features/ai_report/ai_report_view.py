from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.application.state import AppState
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.style import PAGE_MAX_WIDTH, apply_shadow, panel_layout


class AIReportView(QWidget):
    def __init__(self, state: AppState, *, on_back: Callable[[], None], on_reconnect: Callable[[], None]) -> None:
        super().__init__()
        self.state = state

        layout = QVBoxLayout(self)
        self.title = QLabel(gui_t(self.state, "ai_title"))
        self.title.setObjectName("title")
        layout.addWidget(self.title)

        credits_row = QHBoxLayout()
        self.credits_label = QLabel("")
        self.refresh_credits_btn = QPushButton(gui_t(self.state, "refresh_credits"))
        self.manage_credits_btn = QPushButton(gui_t(self.state, "manage_credits"))
        credits_row.addWidget(self.credits_label)
        credits_row.addStretch(1)
        credits_row.addWidget(self.refresh_credits_btn)
        credits_row.addWidget(self.manage_credits_btn)

        credits_card = QFrame()
        credits_card.setObjectName("card")
        apply_shadow(credits_card, blur=14, y=4)
        credits_layout = QHBoxLayout(credits_card)
        credits_layout.setContentsMargins(12, 10, 12, 10)
        self.credits_title = QLabel(gui_t(self.state, "credits_card"))
        self.credits_title.setObjectName("sectionTitle")
        self.buy_credits_btn = QPushButton(gui_t(self.state, "buy_credits"))
        self.buy_credits_btn.setObjectName("primary")
        credits_layout.addWidget(self.credits_title)
        credits_layout.addStretch(1)
        credits_layout.addWidget(self.buy_credits_btn)

        self.notes_label = QLabel(gui_t(self.state, "notes"))
        self.notes = QPlainTextEdit()
        self.notes.setMinimumHeight(90)

        options_row = QHBoxLayout()
        self.use_vin_decode = QCheckBox(gui_t(self.state, "use_vin"))
        self.use_vin_decode.setChecked(True)
        self.generate_btn = QPushButton(gui_t(self.state, "generate"))
        self.generate_btn.setObjectName("primary")
        self.generate_btn.setMinimumWidth(190)
        self.generate_btn.setMinimumHeight(44)
        options_row.addWidget(self.use_vin_decode)
        options_row.addStretch(1)
        options_row.addWidget(self.generate_btn)

        self.status_label = QLabel("")
        self.status_label.setObjectName("hint")
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setVisible(False)

        top_panel, top_layout = panel_layout(padding=16)
        top_panel.setMaximumWidth(PAGE_MAX_WIDTH)
        top_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        top_layout.addLayout(credits_row)
        top_layout.addWidget(credits_card)
        top_layout.addWidget(self.notes_label)
        top_layout.addWidget(self.notes)
        top_layout.addLayout(options_row)
        top_layout.addWidget(self.status_label)
        top_layout.addWidget(self.loading_bar)
        layout.addWidget(top_panel)

        list_panel, list_layout = panel_layout(padding=14)
        list_panel.setMinimumWidth(320)
        self.reports_label = QLabel(gui_t(self.state, "reports_title"))
        list_layout.addWidget(self.reports_label)
        self.retention_note = QLabel("PDFs are stored locally. If deleted, regeneration requires credits.")
        self.retention_note.setObjectName("hint")
        list_layout.addWidget(self.retention_note)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(gui_t(self.state, "search_reports"))
        self.search_input.setMinimumWidth(240)
        self.search_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "complete", "pending", "error"])
        self.status_filter.setMinimumWidth(130)
        self.date_filter = QComboBox()
        self.date_filter.addItems(["All", "Today", "Last 7 days", "Last 30 days"])
        self.date_filter.setMinimumWidth(150)
        self.favorite_btn = QPushButton(gui_t(self.state, "favorite"))
        self.favorite_btn.setObjectName("secondary")
        self.favorite_btn.setMinimumWidth(120)
        filter_row.addWidget(self.search_input)
        filter_row.addWidget(self.status_filter)
        filter_row.addWidget(self.date_filter)
        filter_row.addWidget(self.favorite_btn)
        list_layout.addLayout(filter_row)

        self.report_list = QListWidget()
        list_layout.addWidget(self.report_list)

        list_btn_row = QHBoxLayout()
        list_btn_row.setSpacing(8)
        self.refresh_list_btn = QPushButton(gui_t(self.state, "refresh"))
        self.export_btn = QPushButton(gui_t(self.state, "export"))
        self.view_btn = QPushButton(gui_t(self.state, "viewer"))
        list_btn_row.addWidget(self.refresh_list_btn)
        list_btn_row.addWidget(self.export_btn)
        list_btn_row.addWidget(self.view_btn)
        list_layout.addLayout(list_btn_row)

        preview_panel, preview_layout = panel_layout(padding=14)
        self.preview_label = QLabel(gui_t(self.state, "preview"))
        self.preview_label.setObjectName("sectionTitle")
        preview_layout.addWidget(self.preview_label)
        self.preview_meta = QLabel("")
        self.preview_meta.setObjectName("hint")
        preview_layout.addWidget(self.preview_meta)
        chips_row = QHBoxLayout()
        self.dtc_chip = QLabel("DTCs: —")
        self.dtc_chip.setObjectName("chip")
        self.readiness_chip = QLabel("Readiness: —")
        self.readiness_chip.setObjectName("chip")
        chips_row.addWidget(self.dtc_chip)
        chips_row.addWidget(self.readiness_chip)
        chips_row.addStretch(1)
        preview_layout.addLayout(chips_row)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        preview_layout.addWidget(self.preview)
        preview_actions = QHBoxLayout()
        self.copy_report_btn = QPushButton(gui_t(self.state, "copy_report"))
        self.copy_report_btn.setObjectName("secondary")
        preview_actions.addWidget(self.copy_report_btn)
        preview_actions.addStretch(1)
        preview_layout.addLayout(preview_actions)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(list_panel)
        splitter.addWidget(preview_panel)
        splitter.setSizes([360, 560])
        layout.addWidget(splitter)

        bottom_row = QHBoxLayout()
        self.reconnect_btn = QPushButton(gui_t(self.state, "reconnect"))
        self.reconnect_btn.setObjectName("secondary")
        self.reconnect_btn.clicked.connect(on_reconnect)
        self.back_btn = QPushButton(gui_t(self.state, "back"))
        self.back_btn.setObjectName("primary")
        self.back_btn.clicked.connect(on_back)
        bottom_row.addWidget(self.reconnect_btn)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self.back_btn)
        layout.addLayout(bottom_row)

    def refresh_text(self) -> None:
        self.title.setText(gui_t(self.state, "ai_title"))
        self.notes_label.setText(gui_t(self.state, "notes"))
        self.use_vin_decode.setText(gui_t(self.state, "use_vin"))
        self.generate_btn.setText(gui_t(self.state, "generate"))
        self.refresh_credits_btn.setText(gui_t(self.state, "refresh_credits"))
        self.manage_credits_btn.setText(gui_t(self.state, "manage_credits"))
        self.buy_credits_btn.setText(gui_t(self.state, "buy_credits"))
        self.credits_title.setText(gui_t(self.state, "credits_card"))
        self.reports_label.setText(gui_t(self.state, "reports_title"))
        self.search_input.setPlaceholderText(gui_t(self.state, "search_reports"))
        self.favorite_btn.setText(gui_t(self.state, "favorite"))
        self.refresh_list_btn.setText(gui_t(self.state, "refresh"))
        self.export_btn.setText(gui_t(self.state, "export"))
        self.view_btn.setText(gui_t(self.state, "viewer"))
        self.preview_label.setText(gui_t(self.state, "preview"))
        self.copy_report_btn.setText(gui_t(self.state, "copy_report"))
        self.reconnect_btn.setText(gui_t(self.state, "reconnect"))
        self.back_btn.setText(gui_t(self.state, "back"))
