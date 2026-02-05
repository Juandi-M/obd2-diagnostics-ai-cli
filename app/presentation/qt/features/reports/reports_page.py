from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.application.state import AppState
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.style import apply_shadow, panel_layout
from app.presentation.qt.widgets.scroll import VerticalScrollArea


class ReportsPage(QWidget):
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

        title = QLabel(gui_t(self.state, "reports_title"))
        title.setObjectName("title")
        content_layout.addWidget(title)

        self.report_list = QListWidget()
        self.report_list.itemSelectionChanged.connect(self._load_report)
        list_panel, list_layout = panel_layout(padding=14)
        list_panel.setMinimumWidth(260)
        list_layout.addWidget(self.report_list)

        preview_panel, preview_layout = panel_layout(padding=14)
        self.preview_label = QLabel(gui_t(self.state, "preview"))
        self.preview_label.setObjectName("sectionTitle")
        preview_layout.addWidget(self.preview_label)
        self.preview_tabs = QTabWidget()
        text_tab = QWidget()
        text_layout = QVBoxLayout(text_tab)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        text_layout.addWidget(self.preview)
        copy_row = QHBoxLayout()
        self.copy_full_btn = QPushButton(gui_t(self.state, "copy_report"))
        self.copy_full_btn.setObjectName("secondary")
        self.copy_full_btn.clicked.connect(self._copy_full_report)
        copy_row.addWidget(self.copy_full_btn)
        copy_row.addStretch(1)
        text_layout.addLayout(copy_row)

        meta_tab = QWidget()
        meta_layout = QVBoxLayout(meta_tab)
        summary_card = QFrame()
        summary_card.setObjectName("card")
        apply_shadow(summary_card, blur=12, y=4)
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(12, 10, 12, 10)
        self.summary_file = QLabel("File: —")
        self.summary_file.setObjectName("hint")
        self.summary_vehicle = QLabel("Vehicle: —")
        self.summary_vehicle.setObjectName("hint")
        self.summary_saved = QLabel("Saved at: —")
        self.summary_saved.setObjectName("hint")
        summary_layout.addWidget(self.summary_file)
        summary_layout.addWidget(self.summary_vehicle)
        summary_layout.addWidget(self.summary_saved)
        meta_layout.addWidget(summary_card)
        self.metadata_text = QPlainTextEdit()
        self.metadata_text.setReadOnly(True)
        meta_layout.addWidget(self.metadata_text)

        self.preview_tabs.addTab(text_tab, gui_t(self.state, "text_tab"))
        self.preview_tabs.addTab(meta_tab, gui_t(self.state, "metadata_tab"))
        preview_layout.addWidget(self.preview_tabs)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(list_panel)
        splitter.addWidget(preview_panel)
        splitter.setSizes([280, 580])
        content_layout.addWidget(splitter)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton(gui_t(self.state, "refresh"))
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self._refresh)
        reconnect_btn = QPushButton(gui_t(self.state, "reconnect"))
        reconnect_btn.setObjectName("secondary")
        reconnect_btn.clicked.connect(self.on_reconnect)
        back_btn = QPushButton(gui_t(self.state, "back"))
        back_btn.setObjectName("primary")
        back_btn.clicked.connect(self.on_back)
        btn_row.addWidget(refresh_btn)
        btn_row.addWidget(reconnect_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(back_btn)
        content_layout.addLayout(btn_row)
        content_layout.addStretch(1)

        self.title = title
        self.refresh_btn = refresh_btn
        self.reconnect_btn = reconnect_btn
        self.back_btn = back_btn

    def refresh_text(self) -> None:
        self.title.setText(gui_t(self.state, "reports_title"))
        self.preview_label.setText(gui_t(self.state, "preview"))
        self.preview_tabs.setTabText(0, gui_t(self.state, "text_tab"))
        self.preview_tabs.setTabText(1, gui_t(self.state, "metadata_tab"))
        self.copy_full_btn.setText(gui_t(self.state, "copy_report"))
        self.refresh_btn.setText(gui_t(self.state, "refresh"))
        self.reconnect_btn.setText(gui_t(self.state, "reconnect"))
        self.back_btn.setText(gui_t(self.state, "back"))

        self._refresh()

    def _refresh(self) -> None:
        self.report_list.clear()
        for entry in self.state.session_results:
            title = entry.get("title") or "Scan"
            stamp = entry.get("timestamp") or ""
            item = QListWidgetItem(f"{title} | {stamp}")
            item.setData(Qt.UserRole, entry)
            self.report_list.addItem(item)

    def _load_report(self) -> None:
        item = self.report_list.currentItem()
        if not item:
            return
        entry = item.data(Qt.UserRole)
        if not entry:
            return
        content = entry.get("output", "")
        self.preview.setPlainText(content)
        saved_at = entry.get("timestamp") or "-"
        profile = self.state.vehicle_profile or {}
        if profile.get("make"):
            vehicle = profile.get("make")
            if profile.get("model"):
                vehicle = f"{vehicle} {profile.get('model')}"
        else:
            vehicle = self.state.brand_label or self.state.manufacturer.capitalize()
        title = entry.get("title") or "Scan"
        self.summary_file.setText(f"Title: {title}")
        self.summary_vehicle.setText(f"Vehicle: {vehicle}")
        self.summary_saved.setText(f"Saved at: {saved_at}")
        meta_lines = [f"Title: {title}", f"Saved at: {saved_at}", f"Vehicle: {vehicle}"]
        self.metadata_text.setPlainText("\n".join(meta_lines))

    def _copy_full_report(self) -> None:
        QApplication.clipboard().setText(self.preview.toPlainText())

