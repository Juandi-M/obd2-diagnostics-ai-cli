from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPropertyAnimation, QTimer
from PySide6.QtWidgets import QGraphicsOpacityEffect, QMainWindow, QSizePolicy, QStackedWidget, QWidget

from app.presentation.qt.app_vm import get_vm
from app.presentation.qt.dialogs.message_box import ui_info
from app.presentation.qt.features.ai_report.ai_report_page import AIReportPage
from app.presentation.qt.features.connection.connect_page import ConnectPage
from app.presentation.qt.features.diagnose.diagnose_page import DiagnosePage
from app.presentation.qt.features.live_data.live_data_page import LiveDataPage
from app.presentation.qt.features.menu.main_menu_page import MainMenuPage
from app.presentation.qt.features.module_map.module_map_page import ModuleMapPage
from app.presentation.qt.features.reports.reports_page import ReportsPage
from app.presentation.qt.features.settings.settings_page import SettingsPage
from app.presentation.qt.features.setup.setup_page import SetupPage
from app.presentation.qt.features.start.start_page import StartPage
from app.presentation.qt.features.uds.uds_tools_page import UdsToolsPage
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.shell.app_shell import AppShell
from app.presentation.qt.widgets.toast import Toast


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OBD-II Scanner")
        self.setMinimumSize(920, 600)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.vm = get_vm()
        self.state = self.vm.state
        self.vm.settings_vm.load()
        if not self.state.language:
            self.state.language = "en"
        self._last_language = str(self.state.language or "en")

        self.stack = QStackedWidget()
        self.shell = AppShell(self.state, self._nav_clicked)
        self.shell.set_page(self.stack)
        self.shell.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCentralWidget(self.shell)
        self.shell.reconnect_btn.clicked.connect(self._reconnect)

        self.start_page = StartPage(self.state, self._start_session, self._refresh_status_badges)
        self.setup_page = SetupPage(self.state, self._setup_done)
        self.connect_page = ConnectPage(self.state, self._connected, self._bypass_connection)
        self.menu_page = MainMenuPage(
            self.state,
            self._open_page,
            self._reconnect,
            on_language_change=self._refresh_status_badges,
        )
        self.diagnose_page = DiagnosePage(self.state, self._back_to_menu, self._reconnect, self._open_ai_from_diagnose)
        self.live_page = LiveDataPage(self.state, self._back_to_menu, self._reconnect)
        self.ai_page = AIReportPage(self.state, self._back_to_menu, self._reconnect)
        self.uds_page = UdsToolsPage(self.state, self._back_to_menu, self._reconnect)
        self.module_map_page = ModuleMapPage(self.state, self._back_to_menu, self._reconnect)
        self.reports_page = ReportsPage(self.state, self._back_to_menu, self._reconnect)
        self.settings_page = SettingsPage(self.state, self._back_to_menu, self._reconnect)

        self.stack.addWidget(self.start_page)
        self.stack.addWidget(self.setup_page)
        self.stack.addWidget(self.connect_page)
        self.stack.addWidget(self.menu_page)
        self.stack.addWidget(self.diagnose_page)
        self.stack.addWidget(self.live_page)
        self.stack.addWidget(self.ai_page)
        self.stack.addWidget(self.uds_page)
        self.stack.addWidget(self.module_map_page)
        self.stack.addWidget(self.reports_page)
        self.stack.addWidget(self.settings_page)

        # Keep startup behavior identical to the previous monolith.
        self.stack.setCurrentWidget(self.menu_page)
        self.shell.set_nav_enabled(True)
        self.shell.set_active("menu")
        self._session_vin: Optional[str] = None

        self.status_badges = [
            self.start_page.status_badge,
            self.setup_page.status_badge,
            self.connect_page.status_badge,
        ]
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._refresh_status_badges)
        self.status_timer.setInterval(1500)

    def _start_session(self) -> None:
        self._set_page(self.setup_page, nav_key=None)

    def _setup_done(self) -> None:
        self._set_page(self.connect_page, nav_key=None)

    def _connected(self) -> None:
        if self.state.last_vin and self._session_vin and self.state.last_vin != self._session_vin:
            self._clear_session_results()
        if self.state.last_vin:
            self._session_vin = self.state.last_vin
        self.module_map_page.refresh_data()
        self._set_page(self.menu_page, nav_key="menu")
        self._refresh_status_badges()

    def _bypass_connection(self) -> None:
        self._set_page(self.menu_page, nav_key="menu")
        self._refresh_status_badges()

    def _clear_session_results(self) -> None:
        self.state.session_results = []
        try:
            self.diagnose_page._clear_output()
        except Exception:
            pass
        try:
            self.live_page._stop()
        except Exception:
            pass
        try:
            self.ai_page.preview.clear()
        except Exception:
            pass
        try:
            self.reports_page._refresh()
        except Exception:
            pass

    def _refresh_status_badges(self) -> None:
        for badge in self.status_badges:
            badge.update_text()

        connected = self.state.active_scanner() is not None
        title_state = gui_t(self.state, "connected") if connected else gui_t(self.state, "disconnected")
        self.setWindowTitle(f"{gui_t(self.state, 'app_title')} • {title_state}")

        # Refresh translations only when language changes; avoids extra work every timer tick.
        current_lang = str(self.state.language or "en")
        if current_lang != self._last_language:
            self._refresh_language()
            self._last_language = current_lang

        self.connect_page.update_empty_state()
        self.shell.update_connection_bar()
        self.menu_page.refresh_text()
        self.reports_page._refresh()

    def show_toast(self, message: str) -> None:
        toast = Toast(message, self)
        toast.show_at(self)

    def _refresh_language(self) -> None:
        self.start_page.refresh_text()
        self.setup_page.refresh_text()
        self.connect_page.refresh_text()
        self.menu_page.refresh_text()
        self.diagnose_page.refresh_text()
        self.live_page.refresh_text()
        self.ai_page.refresh_text()
        self.uds_page.refresh_text()
        self.module_map_page.refresh_text()
        self.reports_page.refresh_text()
        self.settings_page.refresh_text()
        self.shell.refresh_text()

    def start_timers(self) -> None:
        self._refresh_status_badges()
        self.status_timer.start()

    def _open_page(self, key: str) -> None:
        if key == "diagnose":
            self._set_page(self.diagnose_page, nav_key="diagnose")
        elif key == "live":
            self._set_page(self.live_page, nav_key="live")
        elif key == "ai":
            self._set_page(self.ai_page, nav_key="ai")
        elif key == "uds":
            self._set_page(self.uds_page, nav_key="uds")
        elif key == "module_map":
            self.module_map_page.refresh_data()
            self._set_page(self.module_map_page, nav_key="module_map")
        elif key == "reports":
            self._set_page(self.reports_page, nav_key="reports")
        elif key == "settings":
            self._set_page(self.settings_page, nav_key="settings")
        else:
            ui_info(self, "Menu", "This section is not wired yet.")

    def _open_ai_from_diagnose(self) -> None:
        self._set_page(self.ai_page, nav_key="ai")

    def _back_to_menu(self) -> None:
        self._set_page(self.menu_page, nav_key="menu")

    def _reconnect(self) -> None:
        try:
            self.state.disconnect_all()
        except Exception:
            pass
        self._set_page(self.connect_page, nav_key=None)
        self._refresh_status_badges()

    def _nav_clicked(self, key: str) -> None:
        if key == "menu":
            self._set_page(self.menu_page, nav_key="menu")
        else:
            self._open_page(key)

    def _set_page(self, widget: QWidget, nav_key: Optional[str]) -> None:
        self.stack.setCurrentWidget(widget)
        # The connection bar is redundant on the setup/connect flow and wastes vertical space.
        self.shell.connection_bar.setVisible(widget not in {self.start_page, self.setup_page, self.connect_page})
        # Tighten top padding on the setup/connect flow so content sits higher in the window.
        if widget in {self.start_page, self.setup_page, self.connect_page}:
            self.shell.content_layout.setContentsMargins(24, 6, 24, 16)
        else:
            self.shell.content_layout.setContentsMargins(24, 16, 24, 20)
        if nav_key:
            self.shell.set_active(nav_key)
        self._fade_in(widget)

    def _fade_in(self, widget: QWidget) -> None:
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", widget)
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)

        def _cleanup() -> None:
            widget.setGraphicsEffect(None)

        anim.finished.connect(_cleanup)
        anim.start()
        self._fade_anim = anim
