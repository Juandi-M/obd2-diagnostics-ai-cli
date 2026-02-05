from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.application.state import AppState
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.style import apply_shadow, panel_layout


class DiagnoseView(QWidget):
    def __init__(
        self,
        state: AppState,
        *,
        on_back: Callable[[], None],
        on_reconnect: Callable[[], None],
        on_ai: Callable[[], None],
    ) -> None:
        super().__init__()
        self.state = state

        layout = QVBoxLayout(self)
        self.title = QLabel(gui_t(self.state, "diagnose_title"))
        self.title.setObjectName("title")
        layout.addWidget(self.title)

        panel, panel_layout_ = panel_layout()
        self.quick_label = QLabel(gui_t(self.state, "quick_actions"))
        self.quick_label.setObjectName("sectionTitle")
        panel_layout_.addWidget(self.quick_label)

        self.full_scan_btn = QPushButton(gui_t(self.state, "full_scan"))
        self.read_codes_btn = QPushButton(gui_t(self.state, "read_codes"))
        self.readiness_btn = QPushButton(gui_t(self.state, "readiness"))
        self.freeze_btn = QPushButton(gui_t(self.state, "freeze_frame"))
        self.quick_clear_btn = QPushButton(gui_t(self.state, "clear_codes_action"))
        self.full_scan_btn.setObjectName("primary")
        for btn in (self.read_codes_btn, self.readiness_btn, self.freeze_btn, self.quick_clear_btn):
            btn.setObjectName("secondary")
        for btn in (self.full_scan_btn, self.read_codes_btn, self.readiness_btn, self.freeze_btn, self.quick_clear_btn):
            btn.setMinimumHeight(44)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        scan_grid = QGridLayout()
        scan_grid.setHorizontalSpacing(14)
        scan_grid.setVerticalSpacing(14)
        scan_grid.setContentsMargins(0, 4, 0, 4)
        scan_grid.addWidget(self.full_scan_btn, 0, 0, 1, 3)
        scan_grid.addWidget(self.read_codes_btn, 1, 0)
        scan_grid.addWidget(self.readiness_btn, 1, 1)
        scan_grid.addWidget(self.freeze_btn, 1, 2)
        scan_grid.addWidget(self.quick_clear_btn, 2, 0, 1, 3)
        for col in range(3):
            scan_grid.setColumnStretch(col, 1)
        panel_layout_.addLayout(scan_grid)

        self.status_label = QLabel("")
        panel_layout_.addWidget(self.status_label)
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setVisible(False)
        panel_layout_.addWidget(self.loading_bar)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(300)
        self.output.setPlaceholderText("Run a scan to see results here.")
        panel_layout_.addWidget(self.output)

        # Code lookup
        self.lookup_label = QLabel(gui_t(self.state, "code_lookup"))
        self.lookup_label.setObjectName("sectionTitle")
        self.lookup_input = QLineEdit()
        self.lookup_input.setPlaceholderText(gui_t(self.state, "code_placeholder"))
        self.lookup_input.setMaximumWidth(240)
        self.lookup_error = QLabel("")
        self.lookup_error.setObjectName("errorText")
        input_col = QVBoxLayout()
        input_col.setSpacing(2)
        input_col.addWidget(self.lookup_input)
        input_col.addWidget(self.lookup_error)
        self.lookup_btn = QPushButton(gui_t(self.state, "lookup"))
        self.lookup_btn.setObjectName("chip")
        self.lookup_clear_btn = QPushButton("✕")
        self.lookup_clear_btn.setObjectName("chip")
        self.lookup_clear_btn.setFixedWidth(30)

        lookup_row = QHBoxLayout()
        lookup_row.addWidget(self.lookup_label)
        lookup_row.addLayout(input_col)
        lookup_row.addWidget(self.lookup_btn)
        lookup_row.addWidget(self.lookup_clear_btn)
        lookup_row.addStretch(1)
        panel_layout_.addLayout(lookup_row)

        self.lookup_card = QFrame()
        self.lookup_card.setObjectName("card")
        apply_shadow(self.lookup_card, blur=12, y=4)
        lookup_layout = QVBoxLayout(self.lookup_card)
        lookup_layout.setContentsMargins(12, 10, 12, 10)
        self.lookup_result_title = QLabel(gui_t(self.state, "code_result"))
        self.lookup_result_title.setObjectName("sectionTitle")
        self.lookup_result_body = QLabel(gui_t(self.state, "code_hint"))
        self.lookup_result_body.setObjectName("hint")
        self.lookup_result_body.setWordWrap(True)
        lookup_layout.addWidget(self.lookup_result_title)
        lookup_layout.addWidget(self.lookup_result_body)
        panel_layout_.addWidget(self.lookup_card)

        # Search
        self.search_card = QFrame()
        self.search_card.setObjectName("card")
        apply_shadow(self.search_card, blur=12, y=4)
        search_layout = QVBoxLayout(self.search_card)
        search_layout.setContentsMargins(12, 10, 12, 10)
        self.search_title = QLabel(gui_t(self.state, "search_codes"))
        self.search_title.setObjectName("sectionTitle")
        search_layout.addWidget(self.search_title)
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(gui_t(self.state, "search_prompt"))
        self.search_btn = QPushButton(gui_t(self.state, "search_button"))
        self.search_btn.setObjectName("chip")
        search_row.addWidget(self.search_input)
        search_row.addWidget(self.search_btn)
        search_layout.addLayout(search_row)
        self.search_results = QListWidget()
        self.search_results.setMaximumHeight(140)
        search_layout.addWidget(self.search_results)
        panel_layout_.addWidget(self.search_card)

        layout.addWidget(panel)

        bottom_row = QHBoxLayout()
        self.clear_btn = QPushButton(gui_t(self.state, "clear"))
        self.copy_btn = QPushButton(gui_t(self.state, "copy"))
        self.copy_btn.setObjectName("secondary")
        self.ai_btn = QPushButton(gui_t(self.state, "ai_interpretation"))
        self.ai_btn.setObjectName("secondary")
        self.ai_btn.clicked.connect(on_ai)
        self.reconnect_btn = QPushButton(gui_t(self.state, "reconnect"))
        self.reconnect_btn.setObjectName("secondary")
        self.reconnect_btn.clicked.connect(on_reconnect)
        self.back_btn = QPushButton(gui_t(self.state, "back"))
        self.back_btn.setObjectName("primary")
        self.back_btn.clicked.connect(on_back)
        bottom_row.addWidget(self.clear_btn)
        bottom_row.addWidget(self.copy_btn)
        bottom_row.addWidget(self.ai_btn)
        bottom_row.addWidget(self.reconnect_btn)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self.back_btn)
        layout.addLayout(bottom_row)

    def refresh_text(self) -> None:
        self.title.setText(gui_t(self.state, "diagnose_title"))
        self.quick_label.setText(gui_t(self.state, "quick_actions"))
        self.full_scan_btn.setText(gui_t(self.state, "full_scan"))
        self.read_codes_btn.setText(gui_t(self.state, "read_codes"))
        self.readiness_btn.setText(gui_t(self.state, "readiness"))
        self.freeze_btn.setText(gui_t(self.state, "freeze_frame"))
        self.quick_clear_btn.setText(gui_t(self.state, "clear_codes_action"))
        self.clear_btn.setText(gui_t(self.state, "clear"))
        self.copy_btn.setText(gui_t(self.state, "copy"))
        self.ai_btn.setText(gui_t(self.state, "ai_interpretation"))
        self.reconnect_btn.setText(gui_t(self.state, "reconnect"))
        self.back_btn.setText(gui_t(self.state, "back"))

        self.lookup_label.setText(gui_t(self.state, "code_lookup"))
        self.lookup_input.setPlaceholderText(gui_t(self.state, "code_placeholder"))
        self.lookup_btn.setText(gui_t(self.state, "lookup"))
        self.lookup_clear_btn.setText("✕")
        self.lookup_result_title.setText(gui_t(self.state, "code_result"))
        if not self.lookup_result_body.text():
            self.lookup_result_body.setText(gui_t(self.state, "code_hint"))

        self.search_title.setText(gui_t(self.state, "search_codes"))
        self.search_input.setPlaceholderText(gui_t(self.state, "search_prompt"))
        self.search_btn.setText(gui_t(self.state, "search_button"))

    def set_busy(self, busy: bool) -> None:
        for btn in (self.full_scan_btn, self.read_codes_btn, self.readiness_btn, self.freeze_btn, self.quick_clear_btn):
            btn.setEnabled(not busy)
        self.lookup_btn.setEnabled(not busy)
        self.clear_btn.setEnabled(not busy)
        self.loading_bar.setVisible(busy)
        self.status_label.setText("Working..." if busy else "")

    def set_output_text(self, text: str) -> None:
        self.output.setPlainText(text)
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def copy_output(self) -> None:
        QApplication.clipboard().setText(self.output.toPlainText())

