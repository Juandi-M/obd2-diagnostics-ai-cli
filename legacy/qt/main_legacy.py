from __future__ import annotations

import json
import math
import re
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QThreadPool, Qt, Signal, QTimer, QPropertyAnimation, QPointF
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QFrame,
    QGraphicsOpacityEffect,
    QProgressBar,
    QGraphicsDropShadowEffect,
    QSpacerItem,
    QSizePolicy,
    QTabWidget,
    QScrollArea,
)
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QFont, QFontDatabase, QTextCursor
from PySide6.QtWidgets import QSplitter

try:  # Optional PDF preview widgets
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView
    _HAS_PDF_PREVIEW = True
except Exception:  # pragma: no cover - optional dependency
    QPdfDocument = None  # type: ignore[assignment]
    QPdfView = None  # type: ignore[assignment]
    _HAS_PDF_PREVIEW = False

from app.application.time_utils import cr_timestamp
from app.domain.entities import ConnectionLostError, NotConnectedError, ScannerError

from app.bootstrap import get_container
from app.domain.entities import PaymentRequiredError
from app.application.state import AppState
from app.domain.entities import ExternalServiceError
from app.bootstrap.runtime import init_environment
from app.presentation.qt.workers import Worker
from app.presentation.qt.viewmodels import (
    ConnectionViewModel,
    ScanViewModel,
    LiveMonitorViewModel,
    AiReportViewModel,
    ReportsViewModel,
    SettingsViewModel,
)


# NOTE: Avoid QMessageBox static helpers (information/warning/...) because they call
# QDialog.exec() (nested event loop). On macOS + BLE (CoreBluetooth via bleak) we
# observed hard crashes (SIGSEGV) when these modal exec dialogs are shown.
# Using a non-blocking modal QMessageBox via .open() avoids the nested event loop.
_ACTIVE_MESSAGE_BOXES: List[QMessageBox] = []


def _show_message_box(parent: Optional[QWidget], title: str, text: str, *, icon: QMessageBox.Icon) -> None:
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.setWindowModality(Qt.WindowModality.WindowModal if parent else Qt.WindowModality.ApplicationModal)
    box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
    _ACTIVE_MESSAGE_BOXES.append(box)

    def _cleanup(_: int) -> None:
        try:
            _ACTIVE_MESSAGE_BOXES.remove(box)
        except ValueError:
            pass
        box.deleteLater()

    box.finished.connect(_cleanup)
    # Defer open to avoid showing dialogs during signal/slot re-entrancy.
    QTimer.singleShot(0, box.open)


def ui_info(parent: Optional[QWidget], title: str, text: str) -> None:
    _show_message_box(parent, title, text, icon=QMessageBox.Icon.Information)


def ui_warn(parent: Optional[QWidget], title: str, text: str) -> None:
    _show_message_box(parent, title, text, icon=QMessageBox.Icon.Warning)


APP_STYLES = """
QWidget {
    background-color: #f7f5ff;
    color: #1d2030;
    font-size: 15px;
}
QLabel {
    background: transparent;
}
QFrame#sidebar {
    background-color: #ffffff;
    border-right: 1px solid #e2def7;
}
QFrame#contentArea {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #f7f4ff, stop:1 #eef2ff);
}
QLabel#sidebarTitle {
    font-size: 18px;
    font-weight: 700;
    color: #2b2b44;
}
QLabel#tag {
    background-color: #eef0ff;
    border: 1px solid #d8d5ff;
    border-radius: 8px;
    padding: 2px 6px;
    font-size: 12px;
    color: #3d3f6a;
}
QPushButton#navButton {
    background-color: transparent;
    color: #3a3d63;
    border: none;
    padding: 10px 12px;
    text-align: left;
    font-weight: 600;
}
QPushButton#navButton:hover { background-color: #f2f1ff; border-radius: 10px; }
QPushButton#navButton[active="true"] {
    background-color: #ecebff;
    border-radius: 10px;
    color: #4338ca;
}
QLabel#title {
    font-size: 26px;
    font-weight: 700;
    color: #24243a;
}
QLabel#subtitle {
    font-size: 15px;
    color: #6b6b88;
}
QLabel#statusBadge {
    font-size: 12px;
    color: #6b6b88;
    background: transparent;
    border: none;
    border-radius: 12px;
    padding: 6px 10px;
}
QLabel#sectionTitle {
    font-size: 18px;
    font-weight: 700;
    color: #3a3d63;
}
QLabel#chip {
    background-color: #eef2ff;
    border: 1px solid #d8d6ef;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    color: #4b4f75;
}
QLabel#hint {
    font-size: 12px;
    color: #7b7f9c;
}
QLabel#errorText {
    font-size: 11px;
    color: #d14343;
}
QTabWidget::pane {
    border: none;
}
QTabBar::tab {
    background-color: #f2f1ff;
    border: 1px solid #d8d6ef;
    padding: 6px 12px;
    border-radius: 8px;
    margin-right: 6px;
    font-size: 13px;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    border: 1px solid #cfcaf0;
}
QPushButton#primary {
    background-color: #6d6cff;
    color: #ffffff;
    border: none;
    padding: 14px 24px;
    border-radius: 12px;
    font-weight: 700;
    font-size: 18px;
}
QPushButton#primary:hover { background-color: #5b59f0; }
QPushButton#primary:pressed { background-color: #4a47d6; }
QPushButton#secondary {
    background-color: #ffffff;
    color: #3a3d63;
    border: 1px solid #d8d6ef;
    padding: 12px 18px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 17px;
}
QPushButton#secondary:hover { background-color: #f2f1ff; }
QPushButton#secondary:pressed { background-color: #e7e5ff; }
QPushButton#danger {
    background-color: #b91c1c;
    color: #ffffff;
    border: none;
    padding: 10px 16px;
    border-radius: 12px;
    font-weight: 700;
    font-size: 15px;
}
QPushButton#danger:hover { background-color: #a31616; }
QPushButton#danger:pressed { background-color: #8f1212; }
QPushButton#ghost {
    background-color: transparent;
    color: #5a5e85;
    border: none;
    padding: 6px 8px;
    font-weight: 600;
}
QPushButton#chip {
    background-color: #eef2ff;
    color: #4b4f75;
    border: 1px solid #d8d6ef;
    padding: 6px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#chip:hover {
    background-color: #e6e8ff;
}
QPushButton#tile {
    border: none;
    border-radius: 16px;
    padding: 20px;
    font-size: 20px;
    font-weight: 700;
    color: #24243a;
}
QPushButton#tile[tileDensity="compact"] {
    font-size: 18px;
    padding: 16px;
}
QPushButton#tile[tileDensity="dense"] {
    font-size: 17px;
    padding: 14px;
}
QPushButton {
    background-color: #ffffff;
    color: #3a3d63;
    border: 1px solid #d8d6ef;
    padding: 10px 16px;
    border-radius: 12px;
    font-size: 16px;
}
QPushButton:hover {
    background-color: #f2f1ff;
    border: 1px solid #cfcaf0;
    border-radius: 12px;
}
QListWidget {
    background-color: #ffffff;
    border: 1px solid #e2def7;
    border-radius: 12px;
    padding: 6px;
}
QPlainTextEdit {
    background-color: #ffffff;
    border: 1px solid #e2def7;
    border-radius: 12px;
    padding: 8px;
    font-family: "Menlo", "Consolas", "Courier New", monospace;
}
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2def7;
    border-radius: 12px;
    gridline-color: #e8e5f7;
}
QHeaderView::section {
    background-color: #f1efff;
    border: none;
    padding: 6px;
}
QLineEdit, QComboBox, QSpinBox {
    background-color: #ffffff;
    border: 1px solid #d8d6ef;
    padding: 8px 12px;
    border-radius: 12px;
    font-size: 16px;
}
QComboBox {
    padding: 8px 34px 8px 12px;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    background: #f6f5ff;
    border-left: 1px solid #d8d6ef;
    border-top-right-radius: 12px;
    border-bottom-right-radius: 12px;
}
QComboBox::down-arrow {
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path d='M1 1l4 4 4-4' stroke='%23414a5a' stroke-width='1.6' fill='none' stroke-linecap='round' stroke-linejoin='round'/></svg>");
    width: 10px;
    height: 6px;
}
QSpinBox {
    padding: 8px 34px 8px 12px;
    min-width: 90px;
}
QSpinBox::up-button, QSpinBox::down-button {
    subcontrol-origin: border;
    width: 28px;
    background: #f6f5ff;
    border-left: 1px solid #d8d6ef;
}
QSpinBox::up-button {
    subcontrol-position: right top;
    border-top-right-radius: 12px;
}
QSpinBox::down-button {
    subcontrol-position: right bottom;
    border-bottom-right-radius: 12px;
}
QSpinBox::up-arrow, QSpinBox::down-arrow {
    width: 10px;
    height: 6px;
}
QSpinBox::up-arrow {
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path d='M1 5l4-4 4 4' stroke='%23414a5a' stroke-width='1.6' fill='none' stroke-linecap='round' stroke-linejoin='round'/></svg>");
}
QSpinBox::down-arrow {
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path d='M1 1l4 4 4-4' stroke='%23414a5a' stroke-width='1.6' fill='none' stroke-linecap='round' stroke-linejoin='round'/></svg>");
}
QComboBox#langSelect {
    border-radius: 12px;
    padding: 8px 34px 8px 12px;
    background-color: #ffffff;
}
QComboBox#langSelect::drop-down {
    width: 28px;
    background: #f6f5ff;
    border-left: 1px solid #d8d6ef;
    border-top-right-radius: 12px;
    border-bottom-right-radius: 12px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    selection-background-color: #6d6cff;
    selection-color: #ffffff;
}
QFrame#card {
    background-color: #ffffff;
    border: 1px solid #ecebfb;
    border-radius: 16px;
}
QFrame#panel {
    background-color: #ffffff;
    border: 1px solid #e8e5ff;
    border-radius: 18px;
}
QFrame#card:hover {
    border: 1px solid #c7c3ff;
}
QFrame#emptyCard {
    background-color: #ffffff;
    border: 1px dashed #d8d6ef;
    border-radius: 14px;
}
QLabel#cardTitle {
    font-size: 14px;
    color: #6b6b88;
}
QLabel#cardValue {
    font-size: 30px;
    font-weight: 800;
    color: #24243a;
}
QProgressBar {
    background-color: #f0eeff;
    border: 1px solid #e2def7;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background-color: #6d6cff;
    border-radius: 6px;
}
QProgressBar#telemetryBar {
    background-color: #eef1f4;
    border: 1px solid #cfd5dc;
    border-radius: 7px;
    height: 14px;
    text-align: center;
    color: #2b3240;
    font-size: 12px;
    font-weight: 600;
}
QProgressBar#telemetryBar::chunk {
    background-color: #2f3a44;
    border-radius: 6px;
}

/* Scrollbars: modern + minimal (avoid arrow buttons / "Windows 95" look) */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 6px 3px 6px 3px;
}
QScrollBar::handle:vertical {
    background: rgba(47, 58, 68, 90);
    min-height: 32px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(47, 58, 68, 140);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}

QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 3px 6px 3px 6px;
}
QScrollBar::handle:horizontal {
    background: rgba(47, 58, 68, 90);
    min-width: 32px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(47, 58, 68, 140);
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
}
"""

PAGE_MAX_WIDTH = 1400

GUI_I18N = {
    "en": {
        "app_title": "OBD-II Scanner",
        "start_session": "Get Started",
        "subtitle": "Fast diagnostics. Clear guidance. Professional reports.",
        "language": "Language",
        "session_setup": "Vehicle Setup",
        "vehicle_library": "Vehicle Library",
        "make": "Make",
        "model": "Model",
        "year": "Year",
        "trim": "Trim",
        "continue": "Continue",
        "connection": "Connection",
        "connect_device": "Connect Device",
        "connect_menu_hint": "Connect an adapter to start scanning.",
        "device": "Device",
        "ready_to_scan": "Ready to scan.",
        "usb": "USB ELM327",
        "ble": "Bluetooth ELM327",
        "scan": "Scan",
        "stop": "Stop",
        "show_all_ble": "Show all BLE devices",
        "connect_hint": "Scan to discover adapters, then select one to connect.",
        "connect_empty_title": "No device connected",
        "connect_empty_body": "Plug in a USB ELM327 or scan for Bluetooth. You can also continue without a device.",
        "connect": "Connect",
        "bypass": "Continue without connection",
        "main_menu": "Main Menu",
        "diagnose": "Diagnose",
        "live": "Live Data",
        "ai_scan": "AI Scan",
        "ai_report": "AI Report",
        "reports": "Reports",
        "settings": "Settings",
        "uds_tools": "UDS Tools",
        "back": "Back",
        "reconnect": "Reconnect",
        "status": "Status",
        "connected": "Connected",
        "disconnected": "Disconnected",
        "vehicle": "Vehicle",
        "vin_label": "VIN",
        "format": "Format",
        "protocol": "Protocol",
        "diagnose_title": "Diagnose",
        "full_scan": "Full Diagnostic Scan",
        "read_codes": "Read Trouble Codes",
        "readiness": "Readiness Monitors",
        "freeze_frame": "Freeze Frame",
        "clear": "Clear",
        "export_pdf": "Export PDF",
        "copy": "Copy",
        "ai_interpretation": "AI Interpretation",
        "copy_report": "Copy Report",
        "text_tab": "Text",
        "metadata_tab": "Metadata",
        "quick_actions": "Quick actions",
        "run_full_scan": "Run Full Scan",
        "clear_codes_action": "Clear Codes",
        "lookup": "Lookup",
        "code_lookup": "Code lookup",
        "code_placeholder": "Enter DTC (e.g., P0420)",
        "code_result": "Lookup result",
        "code_hint": "Enter a code to see details.",
        "code_invalid": "Invalid DTC format.",
        "code_missing": "Enter a DTC code.",
        "search_codes": "Search Codes",
        "search_prompt": "Search descriptions...",
        "search_results": "Search results",
        "search_none": "No codes found.",
        "search_button": "Search",
        "clear_lookup": "Clear",
        "confirm_clear_title": "Clear Codes",
        "confirm_clear_body": "This will erase stored DTCs and reset readiness. Continue?",
        "live_title": "Live Data",
        "telemetry_overview": "Telemetry Overview",
        "telemetry_trends": "Telemetry Trends",
        "telemetry_trends_hint": "Mini trend previews (updates while live telemetry runs).",
        "telemetry_trends_placeholder": "Start telemetry to see trends.",
        "start": "Start",
        "stop": "Stop",
        "interval": "Interval (s)",
        "save_log": "Save log",
        "customize": "Customize",
        "ai_title": "AI Diagnostic Report",
        "notes": "Customer / mechanic notes",
        "use_vin": "Use VIN decode for validation",
        "generate": "Generate Report",
        "buy_credits": "Buy Credits",
        "credits_card": "Need more AI credits?",
        "refresh_credits": "Refresh Credits",
        "manage_credits": "Manage Credits",
        "reports_title": "Reports",
        "refresh": "Refresh",
        "viewer": "View JSON + PDF",
        "export": "Export PDF",
        "preview": "Preview",
        "search_reports": "Search reports...",
        "favorite": "★ Favorite",
        "settings_title": "Settings",
        "module_map": "Module Map",
        "module_map_hint": "Discover ECU modules and build a quick map of IDs, types, and security flags.",
        "module_map_hint_detail": "Use filters to narrow by type, favorites, or security-required modules.",
        "module_map_search": "Search modules...",
        "module_map_all": "All types",
        "module_map_favorites": "Favorites only",
        "module_map_security": "Security only",
        "general": "General",
        "vehicle_section": "Vehicle",
        "logging": "Logging",
        "log_format": "Log format",
        "monitor_interval": "Monitor interval (s)",
        "verbose": "Verbose OBD logging",
        "save": "Save",
        "uds_title": "UDS Tools",
        "uds_brand": "UDS Brand",
        "uds_module": "Module",
        "uds_read_vin": "Read VIN (F190)",
        "uds_read_did": "Read DID",
        "uds_read_dtcs": "Read DTCs (UDS)",
        "uds_send_raw": "Send Raw",
        "uds_service_id": "Service ID (hex)",
        "uds_data_hex": "Data (hex)",
        "uds_response": "Response",
        "uds_no_module": "Select a module first.",
        "uds_not_supported": "UDS tools are not supported on K-Line connections.",
        "uds_discover": "Discover modules",
        "uds_discover_range": "Quick range (7E0-7EF)",
        "uds_discover_29bit": "Include 29-bit",
        "uds_discover_250": "Fallback 250k",
        "uds_discover_timeout": "Timeout (ms)",
        "uds_discover_hint": "Scan CAN IDs for UDS responses (10 03 / 3E 00).",
        "uds_discover_none": "No UDS modules detected.",
        "uds_discover_found": "Modules detected",
        "uds_discover_protocol": "Protocol",
        "uds_discover_vin": "VIN",
        "uds_discover_responses": "Responses",
        "uds_discover_alt_tx": "Alt TX",
        "uds_discover_confidence": "Confidence",
        "uds_discover_security": "Requires security access",
        "uds_discover_dtcs": "Probe DTCs",
        "uds_discover_type": "Type",
        "uds_discover_dtcs_summary": "DTC summary",
        "uds_discover_cached": "Load cached map",
        "uds_discover_cached_label": "Cached VIN map",
        "uds_discover_cached_none": "No cached map for VIN",
        "kline": "K-Line (legacy protocol) fallback (USB)",
        "kline_connected": "Connected via K-Line",
    },
    "es": {
        "app_title": "OBD-II Scanner",
        "start_session": "Comenzar",
        "subtitle": "Diagnósticos rápidos. Guía clara. Reportes profesionales.",
        "language": "Idioma",
        "session_setup": "Configuración del vehículo",
        "vehicle_library": "Biblioteca de vehículos",
        "make": "Marca",
        "model": "Modelo",
        "year": "Año",
        "trim": "Versión",
        "continue": "Continuar",
        "connection": "Conexión",
        "connect_device": "Conectar dispositivo",
        "connect_menu_hint": "Conecta un adaptador para empezar a escanear.",
        "device": "Dispositivo",
        "ready_to_scan": "Listo para escanear.",
        "usb": "USB ELM327",
        "ble": "Bluetooth ELM327",
        "scan": "Buscar",
        "stop": "Detener",
        "show_all_ble": "Mostrar todos los BLE",
        "connect_hint": "Busca adaptadores y selecciona uno para conectar.",
        "connect_empty_title": "Sin dispositivo conectado",
        "connect_empty_body": "Conecta un ELM327 por USB o busca Bluetooth. También puedes continuar sin dispositivo.",
        "connect": "Conectar",
        "bypass": "Continuar sin conexión",
        "main_menu": "Menú principal",
        "diagnose": "Diagnóstico",
        "live": "Datos en vivo",
        "ai_scan": "Escaneo IA",
        "ai_report": "Informe IA",
        "reports": "Reportes",
        "settings": "Configuración",
        "uds_tools": "Herramientas UDS",
        "back": "Atrás",
        "reconnect": "Reconectar",
        "status": "Estado",
        "connected": "Conectado",
        "disconnected": "Desconectado",
        "vehicle": "Vehículo",
        "vin_label": "VIN",
        "format": "Formato",
        "protocol": "Protocolo",
        "diagnose_title": "Diagnóstico",
        "full_scan": "Escaneo completo",
        "read_codes": "Leer códigos",
        "readiness": "Monitores de preparación",
        "freeze_frame": "Datos de congelación",
        "clear": "Limpiar",
        "export_pdf": "Exportar PDF",
        "copy": "Copiar",
        "ai_interpretation": "Interpretación IA",
        "copy_report": "Copiar reporte",
        "text_tab": "Texto",
        "metadata_tab": "Metadatos",
        "quick_actions": "Acciones rápidas",
        "run_full_scan": "Ejecutar escaneo",
        "clear_codes_action": "Borrar códigos",
        "lookup": "Buscar",
        "code_lookup": "Buscar código",
        "code_placeholder": "Ingresa DTC (ej., P0420)",
        "code_result": "Resultado de búsqueda",
        "code_hint": "Ingresa un código para ver detalles.",
        "code_invalid": "Formato de DTC inválido.",
        "code_missing": "Ingresa un DTC.",
        "search_codes": "Buscar códigos",
        "search_prompt": "Buscar descripciones...",
        "search_results": "Resultados",
        "search_none": "No se encontraron códigos.",
        "search_button": "Buscar",
        "clear_lookup": "Limpiar",
        "confirm_clear_title": "Borrar códigos",
        "confirm_clear_body": "Se borrarán DTCs y se reiniciará readiness. ¿Continuar?",
        "live_title": "Datos en vivo",
        "telemetry_overview": "Resumen de telemetría",
        "telemetry_trends": "Tendencias de telemetría",
        "telemetry_trends_hint": "Vistas de tendencia (se actualizan con telemetría en vivo).",
        "telemetry_trends_placeholder": "Inicia la telemetría para ver tendencias.",
        "start": "Iniciar",
        "stop": "Detener",
        "interval": "Intervalo (s)",
        "save_log": "Guardar log",
        "customize": "Personalizar",
        "ai_title": "Informe diagnóstico IA",
        "notes": "Notas del cliente/mecánico",
        "use_vin": "Usar VIN para validar",
        "generate": "Generar informe",
        "buy_credits": "Comprar créditos",
        "credits_card": "¿Necesitas más créditos de IA?",
        "refresh_credits": "Actualizar créditos",
        "manage_credits": "Gestionar créditos",
        "reports_title": "Reportes",
        "refresh": "Actualizar",
        "viewer": "Ver JSON + PDF",
        "export": "Exportar PDF",
        "preview": "Vista previa",
        "search_reports": "Buscar reportes...",
        "favorite": "★ Favorito",
        "settings_title": "Configuración",
        "module_map": "Mapa de módulos",
        "module_map_hint": "Descubre módulos ECU y crea un mapa rápido de IDs, tipos y seguridad.",
        "module_map_hint_detail": "Usa filtros por tipo, favoritos o módulos con seguridad.",
        "module_map_search": "Buscar módulos...",
        "module_map_all": "Todos los tipos",
        "module_map_favorites": "Solo favoritos",
        "module_map_security": "Solo seguridad",
        "general": "General",
        "vehicle_section": "Vehículo",
        "logging": "Registro",
        "log_format": "Formato de log",
        "monitor_interval": "Intervalo del monitor (s)",
        "verbose": "Logs OBD detallados",
        "save": "Guardar",
        "uds_title": "Herramientas UDS",
        "uds_brand": "Marca UDS",
        "uds_module": "Módulo",
        "uds_read_vin": "Leer VIN (F190)",
        "uds_read_did": "Leer DID",
        "uds_read_dtcs": "Leer DTCs (UDS)",
        "uds_send_raw": "Enviar crudo",
        "uds_service_id": "ID de servicio (hex)",
        "uds_data_hex": "Datos (hex)",
        "uds_response": "Respuesta",
        "uds_no_module": "Selecciona un módulo primero.",
        "uds_not_supported": "UDS no está disponible en conexiones K-Line.",
        "uds_discover": "Descubrir módulos",
        "uds_discover_range": "Rango rápido (7E0-7EF)",
        "uds_discover_29bit": "Incluir 29-bit",
        "uds_discover_250": "Fallback 250k",
        "uds_discover_timeout": "Timeout (ms)",
        "uds_discover_hint": "Escanear IDs CAN para respuestas UDS (10 03 / 3E 00).",
        "uds_discover_none": "No se detectaron módulos UDS.",
        "uds_discover_found": "Módulos detectados",
        "uds_discover_protocol": "Protocolo",
        "uds_discover_vin": "VIN",
        "uds_discover_responses": "Respuestas",
        "uds_discover_alt_tx": "TX alternativos",
        "uds_discover_confidence": "Confianza",
        "uds_discover_security": "Requiere acceso de seguridad",
        "uds_discover_dtcs": "Probar DTCs",
        "uds_discover_type": "Tipo",
        "uds_discover_dtcs_summary": "Resumen DTCs",
        "uds_discover_cached": "Cargar mapa en caché",
        "uds_discover_cached_label": "Mapa VIN en caché",
        "uds_discover_cached_none": "No hay mapa para VIN",
        "kline": "K-Line (legacy protocol) fallback (USB)",
        "kline_connected": "Conectado por K-Line",
    },
}


def gui_t(state: AppState, key: str) -> str:
    lang = "es" if str(state.language).lower().startswith("es") else "en"
    return GUI_I18N.get(lang, GUI_I18N["en"]).get(key, key)


class MainViewModel(QObject):
    status_changed = Signal()

    def __init__(self, container) -> None:
        super().__init__()
        self.container = container
        self.state: AppState = container.state
        self.settings = container.settings
        self.connection = container.connection
        self.connection_vm = ConnectionViewModel(container.state, container.connection)
        self.scan_vm = ScanViewModel(container.state, container.scans, container.full_scan_reports)
        self.live_monitor_vm = LiveMonitorViewModel(container.state, container.scans)
        self.reports_vm = ReportsViewModel(container.reports, container.pdf_paths)
        self.ai_report_vm = AiReportViewModel(
            container.ai_reports,
            container.ai_config,
            container.paywall,
            container.reports,
            container.pdf_paths,
            container.document_paths,
            container.scans,
        )
        self.settings_vm = SettingsViewModel(container.state, container.settings, container.vehicles)
        self.uds_discovery = container.uds_discovery
        self.uds_tools = container.uds_tools


_VM: Optional[MainViewModel] = None


def set_vm(vm: MainViewModel) -> None:
    global _VM
    _VM = vm


def get_vm() -> MainViewModel:
    if _VM is None:
        set_vm(MainViewModel(get_container()))
    return _VM


class StatusLabel(QLabel):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        self.setObjectName("statusBadge")
        self.update_text()

    def update_text(self) -> None:
        connected = self.state.active_scanner() is not None
        protocol = "K-LINE" if self.state.kline_scanner and self.state.kline_scanner.is_connected else "OBD2"
        conn_status = f"🟢 {gui_t(self.state, 'connected')}" if connected else f"🔴 {gui_t(self.state, 'disconnected')}"
        profile = self.state.vehicle_profile or {}
        if profile.get("make"):
            vehicle = profile.get("make")
            if profile.get("model"):
                vehicle = f"{vehicle} {profile.get('model')}"
        else:
            vehicle = self.state.brand_label or self.state.manufacturer.capitalize()
        lang = str(self.state.language or "en").upper()
        vin_value = self.state.last_vin or ""
        vin_label = f" | {gui_t(self.state, 'vin_label')}: {vin_value}" if vin_value else ""
        self.setText(
            f"{gui_t(self.state, 'status')}: {conn_status} | {gui_t(self.state, 'vehicle')}: {vehicle}{vin_label} | "
            f"{gui_t(self.state, 'format')}: {self.state.log_format.upper()} | "
            f"{gui_t(self.state, 'protocol')}: {protocol} | {lang}"
        )


class Sparkline(QWidget):
    def __init__(self, max_points: int = 40) -> None:
        super().__init__()
        self.max_points = max_points
        self.values: List[float] = []
        self.setMinimumHeight(36)

    def add_point(self, value: float) -> None:
        self.values.append(float(value))
        if len(self.values) > self.max_points:
            self.values = self.values[-self.max_points :]
        self.update()

    def paintEvent(self, event) -> None:
        if len(self.values) < 2:
            return
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            rect = self.rect()
            min_v = min(self.values)
            max_v = max(self.values)
            span = (max_v - min_v) or 1.0
            step = rect.width() / (len(self.values) - 1)
            pen = QPen(QColor("#2f5d8c"), 3)
            painter.setPen(pen)
            points = []
            for i, v in enumerate(self.values):
                x = rect.left() + i * step
                y = rect.bottom() - (v - min_v) / span * rect.height()
                points.append((x, y))
            for i in range(len(points) - 1):
                painter.drawLine(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])
        finally:
            painter.end()


class Gauge(QWidget):
    def __init__(self, min_value: float = 0.0, max_value: float = 100.0) -> None:
        super().__init__()
        self.min_value = min_value
        self.max_value = max_value
        self.value = min_value
        self.setMinimumHeight(80)

    def set_value(self, value: float) -> None:
        self.value = float(value)
        self.update()

    def paintEvent(self, event) -> None:
        rect = self.rect()
        size = min(rect.width(), rect.height())
        radius = size * 0.45
        center = rect.center()
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)

            arc_rect = rect.adjusted(10, 10, -10, -10)
            start_angle = 0
            sweep_angle = 180

            # Background arc (top semi-circle)
            pen_bg = QPen(QColor("#c9ced6"), 8)
            pen_bg.setCapStyle(Qt.RoundCap)
            painter.setPen(pen_bg)
            painter.drawArc(arc_rect, start_angle * 16, sweep_angle * 16)

            # Value arc
            span = self.max_value - self.min_value or 1.0
            pct = max(0.0, min(1.0, (self.value - self.min_value) / span))
            pen_val = QPen(QColor("#2f3a44"), 8)
            pen_val.setCapStyle(Qt.RoundCap)
            painter.setPen(pen_val)
            painter.drawArc(arc_rect, start_angle * 16, int(sweep_angle * 16 * pct))

            # Tick marks + needle for clearer gauge intent
            tick_pen = QPen(QColor("#6c7380"), 2)
            painter.setPen(tick_pen)
            for i in range(6):
                angle_deg = start_angle + (sweep_angle * i / 5)
                angle = math.radians(angle_deg)
                outer = radius * 0.95
                inner = radius * 0.82
                x1 = center.x() + math.cos(angle) * outer
                y1 = center.y() - math.sin(angle) * outer
                x2 = center.x() + math.cos(angle) * inner
                y2 = center.y() - math.sin(angle) * inner
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

            needle_angle = math.radians(start_angle + sweep_angle * pct)
            needle_pen = QPen(QColor("#1f6fb2"), 3)
            painter.setPen(needle_pen)
            nx = center.x() + math.cos(needle_angle) * radius * 0.75
            ny = center.y() - math.sin(needle_angle) * radius * 0.75
            painter.drawLine(center, QPointF(nx, ny))
            painter.setBrush(QColor("#2f3a44"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(center, 4, 4)
        finally:
            painter.end()


class ChartPanel(QWidget):
    def __init__(self, title: str, max_points: int = 80) -> None:
        super().__init__()
        self.title = title
        self.max_points = max_points
        self.values: List[float] = []
        self.setMinimumHeight(140)

    def add_point(self, value: float) -> None:
        self.values.append(float(value))
        if len(self.values) > self.max_points:
            self.values = self.values[-self.max_points :]
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            rect = self.rect().adjusted(10, 10, -10, -10)

            painter.setPen(QPen(QColor("#3a4350"), 2))
            painter.drawRoundedRect(rect, 8, 8)

            painter.setPen(QPen(QColor("#2c343f"), 1))
            painter.drawText(rect.adjusted(8, 4, -8, -4), Qt.AlignLeft | Qt.AlignTop, self.title)

            if len(self.values) < 2:
                return
            chart_rect = rect.adjusted(6, 22, -6, -6)
            min_v = min(self.values)
            max_v = max(self.values)
            span = (max_v - min_v) or 1.0
            step = chart_rect.width() / (len(self.values) - 1)

            painter.setPen(QPen(QColor("#47515e"), 1, Qt.DashLine))
            for i in range(1, 4):
                y = chart_rect.top() + i * (chart_rect.height() / 4)
                painter.drawLine(chart_rect.left(), y, chart_rect.right(), y)

            painter.setPen(QPen(QColor("#1f6fb2"), 3))
            prev = None
            for i, v in enumerate(self.values):
                x = chart_rect.left() + i * step
                y = chart_rect.bottom() - (v - min_v) / span * chart_rect.height()
                if prev:
                    painter.drawLine(prev[0], prev[1], x, y)
                prev = (x, y)
        finally:
            painter.end()


def apply_shadow(widget: QWidget, blur: int = 18, y: int = 6) -> QGraphicsDropShadowEffect:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setXOffset(0)
    shadow.setYOffset(y)
    shadow.setColor(QColor(109, 108, 255, 50))
    widget.setGraphicsEffect(shadow)
    return shadow


def panel_layout(padding: int = 16) -> Tuple[QFrame, QVBoxLayout]:
    panel = QFrame()
    panel.setObjectName("panel")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(padding, padding, padding, padding)
    layout.setSpacing(10)
    apply_shadow(panel, blur=16, y=5)
    return panel, layout


class VerticalScrollArea(QScrollArea):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignTop)

    def setWidget(self, widget: QWidget) -> None:
        super().setWidget(widget)
        if widget is None:
            return
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout = widget.layout()
        if layout:
            layout.setAlignment(Qt.AlignTop)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        widget = self.widget()
        if widget:
            width = self.viewport().width()
            widget.setMinimumWidth(width)
            widget.setMaximumWidth(width)


class Toast(QFrame):
    def __init__(self, message: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        label = QLabel(message)
        layout.addWidget(label)
        apply_shadow(self, blur=18, y=8)

    def show_at(self, parent: QWidget, duration_ms: int = 2200) -> None:
        self.adjustSize()
        x = parent.width() - self.width() - 24
        y = 24
        self.move(x, y)
        self.show()
        QTimer.singleShot(duration_ms, self.close)


def _short_id(value: Optional[str]) -> str:
    if not value:
        return "-"
    if len(value) <= 8:
        return value
    return f"{value[:4]}...{value[-4:]}"


def add_status_badge(layout: QVBoxLayout, state: AppState) -> StatusLabel:
    badge = StatusLabel(state)
    layout.addWidget(badge)
    return badge


def _header_lines(title: str) -> List[str]:
    return ["", "=" * 60, f"  {title}", "=" * 60]


def _subheader_lines(title: str) -> List[str]:
    return ["", "-" * 40, f"  {title}", "-" * 40]


def _documents_pdf_path(vehicle_payload: Dict[str, Any]) -> Path:
    return Path(get_vm().ai_report_vm.document_pdf_path(vehicle_payload))


def detect_report_language(customer_notes: str, default_language: str) -> str:
    return get_vm().ai_report_vm.detect_report_language(customer_notes, default_language, mode="gui")


def extract_report_parts(response: str) -> Tuple[Optional[Dict[str, Any]], str]:
    return get_vm().ai_report_vm.extract_report_parts(response, mode="gui")


def format_report_summary(response: str) -> str:
    lines = ["-" * 60]
    body_lines = response.strip().splitlines()
    for line in body_lines[:20]:
        lines.append(f"  {line}")
    if len(body_lines) > 20:
        lines.append("  ... (more)")
    return "\n".join(lines)


def build_report_input(
    scan_payload: Dict[str, Any],
    customer_notes: str,
    state: AppState,
    language: str,
    *,
    vehicle_payload: Optional[Dict[str, Any]] = None,
    vehicle_profiles: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return get_vm().ai_report_vm.build_report_input(
        scan_payload,
        customer_notes,
        state,
        language,
        vehicle_payload=vehicle_payload,
        vehicle_profiles=vehicle_profiles,
        mode="gui",
    )


def update_report_status(
    path: Any,
    *,
    status: str,
    response: Optional[str] = None,
    response_raw: Optional[str] = None,
    report_json: Optional[Dict[str, Any]] = None,
    language: Optional[str] = None,
    model: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    get_vm().ai_report_vm.update_report_status(
        str(path),
        status=status,
        response=response,
        response_raw=response_raw,
        report_json=report_json,
        language=language,
        model=model,
        error=error,
    )


class StartPage(QWidget):
    def __init__(
        self,
        state: AppState,
        on_start: Callable[[], None],
        on_language_change: Callable[[], None],
    ) -> None:
        super().__init__()
        self.state = state
        self.on_language_change = on_language_change
        layout = QVBoxLayout(self)
        layout.addStretch(1)
        panel, panel_layout_ = panel_layout(padding=26)
        panel.setMaximumWidth(560)
        title = QLabel(gui_t(self.state, "app_title"))
        title.setObjectName("title")
        subtitle = QLabel(gui_t(self.state, "subtitle"))
        subtitle.setObjectName("subtitle")
        panel_layout_.addWidget(title)
        panel_layout_.addWidget(subtitle)

        lang_row = QHBoxLayout()
        lang_label = QLabel(gui_t(self.state, "language"))
        lang_label.setObjectName("chip")
        self.language_combo = QComboBox()
        self.language_combo.setObjectName("langSelect")
        self.language_combo.addItem("🇺🇸 English", userData="en")
        self.language_combo.addItem("🇪🇸 Español", userData="es")
        self.language_combo.currentIndexChanged.connect(self._set_language)
        lang_row.addWidget(lang_label)
        lang_row.addWidget(self.language_combo)
        lang_row.addStretch(1)
        panel_layout_.addLayout(lang_row)

        start_btn = QPushButton(gui_t(self.state, "start_session"))
        start_btn.setObjectName("primary")
        start_btn.setFixedWidth(260)
        start_btn.setFixedHeight(46)
        start_btn.clicked.connect(on_start)
        start_row = QHBoxLayout()
        start_row.addStretch(1)
        start_row.addWidget(start_btn)
        start_row.addStretch(1)
        panel_layout_.addLayout(start_row)

        layout.addWidget(panel, alignment=Qt.AlignCenter)
        layout.addStretch(2)
        self.status_badge = add_status_badge(layout, self.state)

        # Default language from state if set
        if str(self.state.language).lower().startswith("es"):
            self.language_combo.setCurrentIndex(1)
        self.title = title
        self.subtitle = subtitle
        self.lang_label = lang_label
        self.start_btn = start_btn

    def _set_language(self) -> None:
        code = self.language_combo.currentData()
        if isinstance(code, str):
            self.state.language = code
        self.refresh_text()
        self.on_language_change()

    def refresh_text(self) -> None:
        self.title.setText(gui_t(self.state, "app_title"))
        self.subtitle.setText(gui_t(self.state, "subtitle"))
        self.lang_label.setText(gui_t(self.state, "language"))
        self.start_btn.setText(gui_t(self.state, "start_session"))
        lang_idx = 1 if str(self.state.language).lower().startswith("es") else 0
        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentIndex(lang_idx)
        self.language_combo.blockSignals(False)


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


class ConnectPage(QWidget):
    def __init__(
        self,
        state: AppState,
        on_connected: Callable[[], None],
        on_bypass: Callable[[], None],
    ) -> None:
        super().__init__()
        self.state = state
        self.on_connected = on_connected
        self.on_bypass = on_bypass
        self.connection_vm = get_vm().connection_vm
        self.device_list: List[Tuple[str, str, Optional[int]]] = []
        self._busy: bool = False
        self._scan_request_id: int = 0
        self._connect_request_id: int = 0
        self._active_op: Optional[Tuple[str, int]] = None
        # BLE scans (BleakScanner.discover) only return results when the timeout
        # completes. To make the UI feel "instant", we run several short scans
        # back-to-back and merge results, so the list updates every ~1s.
        self._ble_scan_loop: bool = False
        self._ble_scan_iter: int = 0
        self._ble_scan_max_iters: int = 0
        self._ble_scan_include_all: bool = False
        self._ble_seen: Dict[str, Tuple[str, int]] = {}
        self._ble_scan_timeout_s: float = 1.2

        layout = QVBoxLayout(self)
        title = QLabel(gui_t(self.state, "connection"))
        title.setObjectName("title")
        layout.addWidget(title)

        panel, panel_layout_ = panel_layout()
        panel.setMaximumWidth(PAGE_MAX_WIDTH)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        method_row = QHBoxLayout()
        self.usb_radio = QRadioButton(gui_t(self.state, "usb"))
        self.ble_radio = QRadioButton(gui_t(self.state, "ble"))
        self.usb_radio.setChecked(True)
        method_row.addWidget(self.usb_radio)
        method_row.addWidget(self.ble_radio)
        method_row.addStretch(1)
        panel_layout_.addLayout(method_row)

        self.kline_checkbox = QCheckBox(gui_t(self.state, "kline"))
        self.kline_checkbox.setChecked(True)
        panel_layout_.addWidget(self.kline_checkbox)
        self.usb_radio.toggled.connect(self._toggle_kline)
        self.ble_radio.toggled.connect(self._toggle_kline)
        self.ble_radio.toggled.connect(self._maybe_auto_scan_ble)

        scan_row = QHBoxLayout()
        self.scan_btn = QPushButton(gui_t(self.state, "scan"))
        self.scan_btn.setObjectName("primary")
        self.scan_btn.clicked.connect(self._scan)
        self.show_all_ble = QCheckBox(gui_t(self.state, "show_all_ble"))
        scan_row.addWidget(self.scan_btn)
        scan_row.addWidget(self.show_all_ble)
        scan_row.addStretch(1)
        panel_layout_.addLayout(scan_row)
        hint = QLabel(gui_t(self.state, "connect_hint"))
        hint.setObjectName("hint")
        panel_layout_.addWidget(hint)

        status_row = QHBoxLayout()
        self.busy_bar = QProgressBar()
        self.busy_bar.setRange(0, 0)  # indeterminate
        self.busy_bar.setFixedHeight(10)
        self.busy_bar.setMaximumWidth(220)
        self.busy_bar.setVisible(False)
        self.status_label = QLabel("")
        self.status_label.setObjectName("hint")
        status_row.addWidget(self.busy_bar)
        status_row.addWidget(self.status_label, 1)
        self.stop_btn = QPushButton(gui_t(self.state, "stop"))
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setVisible(False)
        self.stop_btn.clicked.connect(self._stop)
        status_row.addWidget(self.stop_btn)
        panel_layout_.addLayout(status_row)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setTextElideMode(Qt.ElideRight)
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        panel_layout_.addWidget(self.list_widget)

        connect_row = QHBoxLayout()
        connect_row.addStretch(1)
        connect_btn = QPushButton(gui_t(self.state, "connect"))
        connect_btn.setObjectName("primary")
        connect_btn.clicked.connect(self._connect)
        connect_row.addWidget(connect_btn)
        connect_row.addStretch(1)
        panel_layout_.addLayout(connect_row)

        # Status card: always visible, replaces the old bottom "No device connected" box.
        self.status_card = QFrame()
        self.status_card.setObjectName("emptyCard")
        apply_shadow(self.status_card, blur=14, y=4)
        status_layout = QVBoxLayout(self.status_card)
        self.status_title = QLabel(gui_t(self.state, "connect_empty_title"))
        self.status_title.setObjectName("sectionTitle")
        self.status_body = QLabel(gui_t(self.state, "connect_empty_body"))
        self.status_body.setWordWrap(True)
        self.status_meta = QLabel("")
        self.status_meta.setObjectName("hint")
        self.status_meta.setWordWrap(True)
        status_layout.addWidget(self.status_title)
        status_layout.addWidget(self.status_body)
        status_layout.addWidget(self.status_meta)
        panel_layout_.addWidget(self.status_card)

        panel_row = QHBoxLayout()
        panel_row.addStretch(1)
        panel_row.addWidget(panel, 50)
        panel_row.addStretch(1)
        layout.addLayout(panel_row)

        bypass_row = QHBoxLayout()
        bypass_btn = QPushButton(gui_t(self.state, "bypass"))
        bypass_btn.setObjectName("secondary")
        bypass_btn.clicked.connect(self.on_bypass)
        bypass_row.addStretch(1)
        bypass_row.addWidget(bypass_btn)
        bypass_row.addStretch(1)
        layout.addLayout(bypass_row)

        self.status_badge = add_status_badge(layout, self.state)
        self.title = title
        self.bypass_btn = bypass_btn
        self.hint_label = hint
        self.connect_btn = connect_btn
        self._toggle_kline()
        self._refresh_status_card()
        self._adjust_list_height()

        self.connection_vm.usb_scan_finished.connect(self._on_usb_scan)
        self.connection_vm.ble_scan_finished.connect(self._on_ble_scan)
        self.connection_vm.connect_finished.connect(self._on_connect)

    def refresh_text(self) -> None:
        self.title.setText(gui_t(self.state, "connection"))
        self.usb_radio.setText(gui_t(self.state, "usb"))
        self.ble_radio.setText(gui_t(self.state, "ble"))
        self.kline_checkbox.setText(gui_t(self.state, "kline"))
        self.scan_btn.setText(gui_t(self.state, "scan"))
        self.stop_btn.setText(gui_t(self.state, "stop"))
        self.show_all_ble.setText(gui_t(self.state, "show_all_ble"))
        self.bypass_btn.setText(gui_t(self.state, "bypass"))
        self.hint_label.setText(gui_t(self.state, "connect_hint"))
        self.connect_btn.setText(gui_t(self.state, "connect"))
        self.status_title.setText(gui_t(self.state, "connect_empty_title"))
        self.status_body.setText(gui_t(self.state, "connect_empty_body"))
        self._refresh_status_card()

    def _toggle_kline(self) -> None:
        self.kline_checkbox.setEnabled(self.usb_radio.isChecked())
        if not self.usb_radio.isChecked():
            self.kline_checkbox.setChecked(False)

    def update_empty_state(self) -> None:
        # Keep card visible; update content based on connection.
        self._refresh_status_card()

    def _scan(self) -> None:
        if self._busy:
            return
        # Reset any prior BLE scan loop state.
        self._ble_scan_loop = False
        self._ble_seen = {}
        if self.usb_radio.isChecked():
            self._scan_request_id += 1
            req_id = self._scan_request_id
            self._active_op = ("scan_usb", req_id)
            self._set_busy(True, "Scanning adapters…")
            self.connection_vm.scan_usb(request_id=req_id)
            return

        self._set_busy(True, "Scanning adapters…")
        self._start_ble_scan_loop()

    def _maybe_auto_scan_ble(self, checked: bool) -> None:
        if not checked:
            return
        if self._busy:
            return
        # Auto-scan once when Bluetooth is selected to reduce clicks.
        if self.list_widget.count() <= 0:
            QTimer.singleShot(50, self._scan)

    def _start_ble_scan_loop(self) -> None:
        self._ble_scan_loop = True
        self._ble_seen = {}
        self._ble_scan_iter = 0
        self._ble_scan_include_all = self.show_all_ble.isChecked()
        # 5 short scans ~= previous 6s default, but updates UI each iteration.
        self._ble_scan_max_iters = 5
        self._ble_scan_next()

    def _ble_scan_next(self) -> None:
        if not self._ble_scan_loop:
            return
        self._ble_scan_iter += 1
        self._scan_request_id += 1
        req_id = self._scan_request_id
        self._active_op = ("scan_ble", req_id)
        self._set_busy(True, f"Scanning adapters… ({self._ble_scan_iter}/{self._ble_scan_max_iters})")
        self.connection_vm.scan_ble(
            self._ble_scan_include_all,
            request_id=req_id,
            timeout_s=self._ble_scan_timeout_s,
        )

    def _on_usb_scan(self, result: Any, err: Any) -> None:
        req_id, ports = (None, None)
        if isinstance(result, tuple) and len(result) == 2:
            req_id, ports = result
        else:
            ports = result
        if self._active_op != ("scan_usb", req_id):
            return
        self._active_op = None
        self._set_busy(False, "")
        if err:
            ui_warn(self, "USB", f"Scan error: {err}")
            return
        ports = ports or []
        self.device_list = []
        for port in ports:
            self.device_list.append((port, port, None))
        self._populate_list()
        self._adjust_list_height()
        if ports:
            self.state.last_seen_at = time.time()
            self.state.last_seen_device = ports[0]
            self.state.last_seen_rssi = None
        if not ports:
            ui_info(self, "USB", "No USB adapters detected.")
        self._refresh_status_card()

    def _on_ble_scan(self, result: Any, err: Any) -> None:
        req_id, payload = (None, None)
        if isinstance(result, tuple) and len(result) == 2:
            req_id, payload = result
        else:
            payload = result
        if self._active_op != ("scan_ble", req_id):
            return
        self._active_op = None
        if err:
            self._ble_scan_loop = False
            self._set_busy(False, "")
            ui_warn(self, "Bluetooth", f"Scan error: {err}")
            return
        devices, ble_err = payload
        if ble_err:
            # Keep scanning; some runs can fail transiently on macOS.
            self.status_label.setText(f"Bluetooth scan warning: {ble_err}")

        devices_list = list(devices or [])
        # Merge results across iterations so the list "fills in" quickly.
        for port, name, rssi in devices_list:
            try:
                rssi_i = int(rssi) if rssi is not None else -999
            except Exception:
                rssi_i = -999
            prev = self._ble_seen.get(port)
            if prev is None or rssi_i > prev[1]:
                self._ble_seen[port] = (str(name), rssi_i)

        merged = [(port, name, rssi) for port, (name, rssi) in self._ble_seen.items()]
        # If the user asked to show all BLE devices, still prioritize likely OBD adapters at the top
        # to avoid accidental selection of headphones/phones.
        self.device_list = self._sort_devices(merged)
        self._populate_list()
        self._adjust_list_height()
        if self.device_list:
            best = self.device_list[0]
            self.state.last_seen_at = time.time()
            self.state.last_seen_device = best[1]
            self.state.last_seen_rssi = best[2] if len(best) > 2 else None
        self._refresh_status_card()

        # Continue/stop the loop.
        found_any = bool(self.device_list)
        found_adapter = any(self._looks_like_obd_adapter(name) for _, name, _ in self.device_list)
        done = False
        if found_any and not self._ble_scan_include_all:
            done = True  # filtered mode; first hit is enough
        elif found_adapter:
            done = True  # show-all mode; stop once we see a likely adapter
        elif self._ble_scan_iter >= self._ble_scan_max_iters:
            done = True

        if not self._ble_scan_loop:
            done = True

        if done:
            self._ble_scan_loop = False
            self._set_busy(False, "")
            if not self.device_list:
                ui_info(self, "Bluetooth", "No BLE adapters detected.")
            return

        # Small delay to let the UI breathe.
        QTimer.singleShot(120, self._ble_scan_next)

    def _populate_list(self) -> None:
        selected_port = None
        cur = self.list_widget.currentItem()
        if isinstance(cur, QListWidgetItem):
            selected_port = cur.data(Qt.UserRole)

        self.list_widget.clear()
        for port, name, rssi in self.device_list:
            label = self._format_device_label(port, name, rssi)
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, port)
            self.list_widget.addItem(item)
        if selected_port is not None:
            for i in range(self.list_widget.count()):
                it = self.list_widget.item(i)
                if it and it.data(Qt.UserRole) == selected_port:
                    self.list_widget.setCurrentRow(i)
                    return
        self._select_preferred_device()

    def _connect(self) -> None:
        current = self.list_widget.currentItem()
        if not current:
            ui_info(self, "Connect", "Select a device first.")
            return
        port = current.data(Qt.UserRole)
        use_kline = self.kline_checkbox.isChecked()
        self._connect_request_id += 1
        req_id = self._connect_request_id
        self._active_op = ("connect", req_id)
        self._set_busy(True, "Connecting / handshaking…")
        self.connection_vm.connect_device(port, use_kline, request_id=req_id)

    def _on_connect(self, result: Any, err: Any) -> None:
        req_id, payload = (None, None)
        if isinstance(result, tuple) and len(result) == 2:
            req_id, payload = result
        else:
            payload = result
        if self._active_op != ("connect", req_id):
            return
        self._active_op = None
        self._set_busy(False, "")
        if err:
            ui_warn(self, "Connect", f"Connection error: {err}")
            self._refresh_status_card(extra_error=str(err))
            return
        mode = payload.get("mode") if isinstance(payload, dict) else None
        info = payload.get("info") if isinstance(payload, dict) else None
        exc = payload.get("error") if isinstance(payload, dict) else None
        if mode not in {"obd", "kline"}:
            ui_warn(self, "Connect", f"Failed: {exc}")
            self._refresh_status_card(extra_error=str(exc) if exc else "Failed")
            return
        if isinstance(self.list_widget.currentItem(), QListWidgetItem):
            port = self.list_widget.currentItem().data(Qt.UserRole)
            if isinstance(port, str) and port.startswith("ble:"):
                self.state.last_ble_address = port.split(":", 1)[1]
                get_vm().settings_vm.save()
        if isinstance(info, dict):
            self.state.last_vin = info.get("vin") or self.state.last_vin
        self.state.last_seen_at = time.time()
        if mode == "kline":
            window = self.window()
            if hasattr(window, "show_toast"):
                window.show_toast(gui_t(self.state, "kline_connected"))
        self._refresh_status_card()
        self.on_connected()

    # connection logic moved to ConnectionViewModel

    def _stop(self) -> None:
        # Best-effort cancellation: we can't reliably cancel a running BLE scan/connect
        # in the thread pool, but we can immediately unblock the UI and ignore stale results.
        op = self._active_op
        self._ble_scan_loop = False
        self._active_op = None
        if op and op[0] == "connect":
            try:
                self.state.disconnect_all()
            except Exception:
                pass
        self._set_busy(False, "Cancelled.")
        self._refresh_status_card()

        def _restore() -> None:
            if not self._busy:
                self._sync_status_label()

        QTimer.singleShot(1600, _restore)

    def _set_busy(self, busy: bool, text: str) -> None:
        self._busy = busy
        self.busy_bar.setVisible(busy)
        self.stop_btn.setVisible(busy)
        if busy:
            self.status_label.setText(text)
        else:
            if text:
                self.status_label.setText(text)
            else:
                self._sync_status_label()
        self.scan_btn.setEnabled(not busy)
        self.connect_btn.setEnabled(not busy)
        self.usb_radio.setEnabled(not busy)
        self.ble_radio.setEnabled(not busy)
        self.kline_checkbox.setEnabled(not busy and self.usb_radio.isChecked())
        self.show_all_ble.setEnabled(not busy)
        self.list_widget.setEnabled(not busy)

    def _sync_status_label(self) -> None:
        current = self.list_widget.currentItem()
        if isinstance(current, QListWidgetItem):
            port = current.data(Qt.UserRole)
            if isinstance(port, str):
                self.status_label.setText(f"Selected: {self._format_selected_summary(port)}")
                return
        self.status_label.setText("")

    def _on_selection_changed(self, current: Optional[QListWidgetItem], _: Optional[QListWidgetItem]) -> None:
        if not current:
            self._sync_status_label()
            return
        port = current.data(Qt.UserRole)
        if isinstance(port, str):
            # Keep this line compact; detailed state lives in the status card.
            self.status_label.setText(f"Selected: {self._format_selected_summary(port)}")

    def _format_selected_summary(self, port: str) -> str:
        for p, name, rssi in self.device_list:
            if p != port:
                continue
            name_s = (str(name) or "").strip() or "-"
            rssi_s = f"{rssi} dBm" if isinstance(rssi, int) and rssi > -999 else None
            parts = [name_s, self._format_port_short(port)]
            if rssi_s:
                parts.append(rssi_s)
            return " • ".join(parts)
        return self._format_port_short(port)

    def _format_port_short(self, port: str) -> str:
        p = str(port)
        if p.startswith("ble:"):
            addr = p.split(":", 1)[1]
            return f"BLE • …{addr[-5:]}" if len(addr) > 6 else f"BLE • {addr}"
        if p.startswith("/dev/"):
            return f"USB • {p.split('/')[-1]}"
        return p

    def _format_device_label(self, port: str, name: str, rssi: Optional[int]) -> str:
        port_s = str(port)
        name_s = (str(name) or "").strip() or "-"
        rssi_s = f"{rssi} dBm" if isinstance(rssi, int) and rssi > -999 else None

        if port_s.startswith("ble:"):
            addr = port_s.split(":", 1)[1]
            short = f"…{addr[-5:]}" if len(addr) > 6 else addr
            parts = [f"{name_s}", f"BLE {short}"]
            if rssi_s:
                parts.append(rssi_s)
            return " • ".join(parts)

        if port_s.startswith("/dev/"):
            dev = port_s.split("/")[-1]
            return f"{dev} • USB serial"

        return f"{name_s} • {port_s}"

    def _looks_like_obd_adapter(self, name: str) -> bool:
        n = (name or "").lower()
        return any(
            token in n
            for token in (
                "veepeak",
                "obd",
                "obdlink",
                "vlinker",
                "elm",
                "car scanner",
                "scan tool",
                "scantool",
                "diagnostic",
                "vgate",
            )
        )

    def _score_device(self, port: str, name: str, rssi: Optional[int]) -> int:
        n = (name or "").strip()
        score = 0
        if self._looks_like_obd_adapter(n):
            score += 1000
        # Strongly de-prioritize common non-adapter BLE devices when showing everything.
        nn = n.lower()
        if any(token in nn for token in ("airpods", "iphone", "watch", "macbook", "ipad")):
            score -= 800
        if isinstance(rssi, int) and rssi > -999:
            # RSSI is negative; closer to 0 is better. Map [-100..0] -> [0..100].
            score += max(0, min(100, 100 + rssi))
        # Prefer explicit BLE ports slightly when scores tie.
        if str(port).startswith("ble:"):
            score += 10
        return score

    def _sort_devices(self, devices: List[Tuple[str, str, Optional[int]]]) -> List[Tuple[str, str, Optional[int]]]:
        return sorted(devices, key=lambda d: self._score_device(d[0], d[1], d[2] if len(d) > 2 else None), reverse=True)

    def _select_preferred_device(self) -> None:
        if self.list_widget.count() <= 0:
            return
        # If "show all" is enabled, auto-select the first likely OBD adapter if present.
        # Otherwise select the first item (already filtered to adapters).
        preferred_row = 0
        if self.show_all_ble.isChecked():
            for idx, (_, name, _) in enumerate(self.device_list):
                if self._looks_like_obd_adapter(name):
                    preferred_row = idx
                    break
            else:
                # Don't auto-select random devices when everything is shown.
                self.list_widget.setCurrentRow(-1)
                return
        self.list_widget.setCurrentRow(preferred_row)

    def _adjust_list_height(self) -> None:
        # Keep the list tight: expand to content up to a cap, then scroll.
        count = self.list_widget.count()
        if count <= 0:
            self.list_widget.setMaximumHeight(120)
            return
        row_h = self.list_widget.sizeHintForRow(0) or 28
        visible_rows = min(count, 8)
        extra = 2 * self.list_widget.frameWidth() + 6
        self.list_widget.setMaximumHeight(row_h * visible_rows + extra)

    def _refresh_status_card(self, extra_error: Optional[str] = None) -> None:
        connected = self.state.active_scanner() is not None
        if connected:
            self.status_title.setText("Connected")
            body = "Adapter connected. You can start scanning from Diagnose or Live Data."
        else:
            self.status_title.setText(gui_t(self.state, "connect_empty_title"))
            body = gui_t(self.state, "connect_empty_body")
        self.status_body.setText(body)

        last_seen = getattr(self.state, "last_seen_device", None) or "-"
        last_rssi = getattr(self.state, "last_seen_rssi", None)
        last_rssi_s = f"{last_rssi} dBm" if isinstance(last_rssi, int) and last_rssi > -999 else "-"
        vin = getattr(self.state, "last_vin", None) or "-"
        protocol = "K-LINE" if getattr(self.state, "kline_scanner", None) is not None else "OBD2"
        selected = "-"
        cur = self.list_widget.currentItem()
        if isinstance(cur, QListWidgetItem):
            p = cur.data(Qt.UserRole)
            if isinstance(p, str):
                selected = self._format_port_short(p)
        meta_lines = [
            f"Selected: {selected}",
            f"Last seen: {last_seen} | Signal: {last_rssi_s}",
            f"Protocol: {protocol} | VIN: {vin}",
        ]
        if extra_error:
            meta_lines.append(f"Last error: {extra_error}")
            meta_lines.append("Tip: ignition ON, wait 10–15s after key-on, then reconnect.")
        self.status_meta.setText("\n".join(meta_lines))


class MainMenuPage(QWidget):
    def __init__(self, state: AppState, on_select: Callable[[str], None], on_reconnect: Callable[[], None]) -> None:
        super().__init__()
        self.state = state
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

        title = QLabel(gui_t(self.state, "main_menu"))
        title.setObjectName("title")
        content_layout.addWidget(title)

        connect_panel = QFrame()
        connect_panel.setObjectName("card")
        connect_panel.setMaximumWidth(PAGE_MAX_WIDTH)
        connect_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        apply_shadow(connect_panel, blur=16, y=6)
        connect_layout = QHBoxLayout(connect_panel)
        connect_layout.setContentsMargins(18, 16, 18, 16)
        connect_title = QLabel(gui_t(self.state, "device"))
        connect_title.setObjectName("sectionTitle")
        status = gui_t(self.state, "connected") if self.state.active_scanner() else gui_t(self.state, "disconnected")
        hint_text = (
            gui_t(self.state, "ready_to_scan")
            if self.state.active_scanner()
            else gui_t(self.state, "connect_menu_hint")
        )
        connect_hint = QLabel(f"{status} · {hint_text}")
        connect_hint.setObjectName("hint")
        left_col = QVBoxLayout()
        left_col.addWidget(connect_title)
        left_col.addWidget(connect_hint)
        left_col.addStretch(1)
        connect_btn = QPushButton(gui_t(self.state, "connect_device"))
        connect_btn.setObjectName("primary")
        connect_btn.setMinimumWidth(190)
        connect_btn.clicked.connect(self.on_reconnect)
        connect_layout.addLayout(left_col)
        connect_layout.addStretch(1)
        connect_layout.addWidget(connect_btn)
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

        self.tile_icons = {
            "diagnose": "🧪",
            "live": "📈",
            "ai": "✨",
            "reports": "🗂️",
            "settings": "⚙️",
            "uds": "🛠️",
            "module_map": "🗺️",
        }
        self.tiles = [
            {
                "label_key": "ai_scan",
                "color": "#d0d4dc",
                "nav_key": "ai",
                "icon_key": "ai",
                "full_width": True,
                "min_height": 160,
            },
            {"label_key": "diagnose", "color": "#c6d0da", "nav_key": "diagnose", "icon_key": "diagnose"},
            {"label_key": "live", "color": "#c6d6cc", "nav_key": "live", "icon_key": "live"},
            {"label_key": "reports", "color": "#d3c8bb", "nav_key": "reports", "icon_key": "reports"},
            {"label_key": "settings", "color": "#d8c7a3", "nav_key": "settings", "icon_key": "settings"},
            {"label_key": "uds_tools", "color": "#d0b7ad", "nav_key": "uds", "icon_key": "uds"},
            {"label_key": "module_map", "color": "#c9ced9", "nav_key": "module_map", "icon_key": "module_map"},
        ]
        self.tile_buttons: List[Tuple[QPushButton, Dict[str, Any]]] = []
        for spec in self.tiles:
            icon = self.tile_icons.get(spec["icon_key"], "")
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

        self.tiles_panel = tiles_panel
        self.tiles_layout = tiles_layout
        self.connect_wrap = connect_wrap
        self.tiles_wrap = tiles_wrap
        self.connect_panel = connect_panel
        self._current_columns = 0
        self._wrap_wide = None
        self._rebuild_grid(self._columns_for_width(self.width()))
        self._update_wrap_stretch(self.width())

        self.title = title
        self.connect_title = connect_title
        self.connect_hint = connect_hint
        self.connect_btn = connect_btn

    def refresh_text(self) -> None:
        self.title.setText(gui_t(self.state, "main_menu"))
        for btn, spec in self.tile_buttons:
            icon = self.tile_icons.get(spec["icon_key"], "")
            btn.setText(f"{icon} {gui_t(self.state, spec['label_key'])}".strip())
        self.connect_title.setText(gui_t(self.state, "device"))
        status = gui_t(self.state, "connected") if self.state.active_scanner() else gui_t(self.state, "disconnected")
        hint_text = (
            gui_t(self.state, "ready_to_scan")
            if self.state.active_scanner()
            else gui_t(self.state, "connect_menu_hint")
        )
        self.connect_hint.setText(f"{status} · {hint_text}")
        self.connect_btn.setText(gui_t(self.state, "connect_device"))

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if not hasattr(self, "tiles_panel"):
            return
        width = self.width()
        columns = self._columns_for_width(width)
        if columns != self._current_columns:
            self._rebuild_grid(columns)
        else:
            self._apply_tile_density(columns, height=self.height())
        self._update_wrap_stretch(width)

    def _columns_for_width(self, width: int) -> int:
        if width >= 980:
            return 3
        if width >= 640:
            return 2
        return 1

    def _rebuild_grid(self, columns: int) -> None:
        if columns < 1:
            columns = 1
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().setParent(self.tiles_panel)
        self._apply_tile_density(columns, height=self.height())
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

    def _apply_tile_density(self, columns: int, height: Optional[int] = None) -> None:
        height = height or self.height()
        if columns >= 3:
            spacing = 14
            padding = 16
            density = ""
            tile_height = 140
            hero_height = 160
        elif columns == 2:
            spacing = 12
            padding = 14
            density = "compact"
            tile_height = 120
            hero_height = 140
        else:
            spacing = 10
            padding = 12
            density = "dense"
            tile_height = 110
            hero_height = 130
        if height < 700:
            spacing = max(8, spacing - 2)
            padding = max(10, padding - 2)
            tile_height = max(96, tile_height - 14)
            hero_height = max(110, hero_height - 20)
            density = "dense" if density == "compact" else density or "compact"
        self.grid.setSpacing(spacing)
        if hasattr(self, "tiles_layout"):
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
        self.connect_wrap.invalidate()
        self.tiles_wrap.invalidate()
        self._wrap_wide = wide


class PaywallDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Paywall / Credits")
        self.paywall = get_vm().ai_report_vm
        self.thread_pool = QThreadPool.globalInstance()

        layout = QVBoxLayout(self)
        self.api_label = QLabel()
        self.subject_label = QLabel()
        self.balance_label = QLabel()
        self.pending_label = QLabel()
        layout.addWidget(self.api_label)
        layout.addWidget(self.subject_label)
        layout.addWidget(self.balance_label)
        layout.addWidget(self.pending_label)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("primary")
        refresh_btn.clicked.connect(self._refresh)
        checkout_btn = QPushButton("Checkout")
        checkout_btn.clicked.connect(self._checkout)
        reset_btn = QPushButton("Reset Identity")
        reset_btn.clicked.connect(self._reset_identity)
        btn_row.addWidget(refresh_btn)
        btn_row.addWidget(checkout_btn)
        btn_row.addWidget(reset_btn)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh()

    def _refresh(self) -> None:
        api_base = self.paywall.api_base() or "-"
        self.api_label.setText(f"API Base: {api_base}")
        subject = _short_id(self.paywall.subject_id() or "")
        self.subject_label.setText(f"Subject ID: {subject}")
        if not self.paywall.is_configured():
            cached = self.paywall.cached_balance()
            pending = self.paywall.pending_total()
            if cached:
                self.balance_label.setText(f"Cached balance: {cached[0]} free / {cached[1]} paid")
            else:
                self.balance_label.setText("Cached balance: -")
            self.pending_label.setText(f"Pending: {pending}")
            return
        self.balance_label.setText("Balance: …")
        self.pending_label.setText("Pending: …")

        def job():
            balance = self.paywall.get_balance()
            pending = self.paywall.pending_total()
            return balance, pending

        worker = Worker(job)
        worker.signals.finished.connect(self._refresh_done)
        self.thread_pool.start(worker)

    def _refresh_done(self, result: Optional[Tuple[Any, int]], exc: Optional[Exception]) -> None:
        if exc:
            QMessageBox.warning(self, "Paywall", f"Failed to refresh balance: {exc}")
            return
        if not result:
            self.balance_label.setText("Balance: -")
            self.pending_label.setText("Pending: -")
            return
        balance, pending = result
        self.balance_label.setText(
            f"Balance: {balance.free_remaining} free / {balance.paid_credits} paid"
        )
        self.pending_label.setText(f"Pending: {pending}")

    def _checkout(self) -> None:
        if not self.paywall.is_configured():
            QMessageBox.warning(self, "Paywall", "Paywall API base not configured.")
            return
        def job():
            return self.paywall.checkout()

        worker = Worker(job)
        worker.signals.finished.connect(self._checkout_done)
        self.thread_pool.start(worker)

    def _checkout_done(self, result: Optional[str], exc: Optional[Exception]) -> None:
        if exc:
            QMessageBox.warning(self, "Paywall", f"Checkout failed: {exc}")
            return
        if result:
            webbrowser.open(result)

    def _reset_identity(self) -> None:
        self.paywall.reset_identity()
        QMessageBox.information(self, "Paywall", "Identity reset.")
        self._refresh()


class DiagnosePage(QWidget):
    def __init__(
        self,
        state: AppState,
        on_back: Callable[[], None],
        on_reconnect: Callable[[], None],
        on_ai: Callable[[], None],
    ) -> None:
        super().__init__()
        self.state = state
        self.on_back = on_back
        self.on_reconnect = on_reconnect
        self.on_ai = on_ai
        self.thread_pool = QThreadPool.globalInstance()
        self.last_output: List[str] = []
        self._pending_label: Optional[str] = None

        layout = QVBoxLayout(self)
        title = QLabel(gui_t(self.state, "diagnose_title"))
        title.setObjectName("title")
        layout.addWidget(title)

        panel, panel_layout_ = panel_layout()
        quick_label = QLabel(gui_t(self.state, "quick_actions"))
        quick_label.setObjectName("sectionTitle")
        panel_layout_.addWidget(quick_label)

        self.full_scan_btn = QPushButton(gui_t(self.state, "full_scan"))
        self.read_codes_btn = QPushButton(gui_t(self.state, "read_codes"))
        self.readiness_btn = QPushButton(gui_t(self.state, "readiness"))
        self.freeze_btn = QPushButton(gui_t(self.state, "freeze_frame"))
        self.quick_clear_btn = QPushButton(gui_t(self.state, "clear_codes_action"))
        self.full_scan_btn.setObjectName("primary")
        self.read_codes_btn.setObjectName("secondary")
        self.readiness_btn.setObjectName("secondary")
        self.freeze_btn.setObjectName("secondary")
        self.quick_clear_btn.setObjectName("secondary")
        for btn in (self.full_scan_btn, self.read_codes_btn, self.readiness_btn, self.freeze_btn):
            btn.setMinimumHeight(44)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(self._handle_action)
        self.quick_clear_btn.setMinimumHeight(44)
        self.quick_clear_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.quick_clear_btn.clicked.connect(self._run_clear_codes)
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
        self.lookup_btn.clicked.connect(self._lookup_code)
        self.lookup_clear_btn = QPushButton("✕")
        self.lookup_clear_btn.setObjectName("chip")
        self.lookup_clear_btn.setFixedWidth(30)
        self.lookup_clear_btn.clicked.connect(self._clear_lookup)
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
        self.search_btn.clicked.connect(self._search_codes)
        self.search_input.returnPressed.connect(self._search_codes)
        search_row.addWidget(self.search_input)
        search_row.addWidget(self.search_btn)
        search_layout.addLayout(search_row)
        self.search_results = QListWidget()
        self.search_results.setMaximumHeight(140)
        search_layout.addWidget(self.search_results)
        panel_layout_.addWidget(self.search_card)
        layout.addWidget(panel)

        bottom_row = QHBoxLayout()
        clear_btn = QPushButton(gui_t(self.state, "clear"))
        clear_btn.clicked.connect(self._clear_output)
        export_btn = None
        copy_btn = QPushButton(gui_t(self.state, "copy"))
        copy_btn.setObjectName("secondary")
        copy_btn.clicked.connect(self._copy_output)
        ai_btn = QPushButton(gui_t(self.state, "ai_interpretation"))
        ai_btn.setObjectName("secondary")
        ai_btn.clicked.connect(self.on_ai)
        reconnect_btn = QPushButton(gui_t(self.state, "reconnect"))
        reconnect_btn.setObjectName("secondary")
        reconnect_btn.clicked.connect(self.on_reconnect)
        back_btn = QPushButton(gui_t(self.state, "back"))
        back_btn.setObjectName("primary")
        back_btn.clicked.connect(self.on_back)
        bottom_row.addWidget(clear_btn)
        bottom_row.addWidget(copy_btn)
        bottom_row.addWidget(ai_btn)
        bottom_row.addWidget(reconnect_btn)
        bottom_row.addStretch(1)
        bottom_row.addWidget(back_btn)
        layout.addLayout(bottom_row)

        self.title = title
        self.clear_btn = clear_btn
        self.copy_btn = copy_btn
        self.ai_btn = ai_btn
        self.reconnect_btn = reconnect_btn
        self.back_btn = back_btn
        self.quick_label = quick_label
        self.lookup_label = self.lookup_label
        self.lookup_error = self.lookup_error
        self.lookup_result_title = self.lookup_result_title
        self.lookup_result_body = self.lookup_result_body
        self.lookup_clear_btn = self.lookup_clear_btn
        self.search_title = self.search_title
        self.search_btn = self.search_btn

    def refresh_text(self) -> None:
        self.title.setText(gui_t(self.state, "diagnose_title"))
        self.full_scan_btn.setText(gui_t(self.state, "full_scan"))
        self.read_codes_btn.setText(gui_t(self.state, "read_codes"))
        self.readiness_btn.setText(gui_t(self.state, "readiness"))
        self.freeze_btn.setText(gui_t(self.state, "freeze_frame"))
        self.clear_btn.setText(gui_t(self.state, "clear"))
        self.copy_btn.setText(gui_t(self.state, "copy"))
        self.ai_btn.setText(gui_t(self.state, "ai_interpretation"))
        self.reconnect_btn.setText(gui_t(self.state, "reconnect"))
        self.back_btn.setText(gui_t(self.state, "back"))
        self.quick_label.setText(gui_t(self.state, "quick_actions"))
        self.quick_clear_btn.setText(gui_t(self.state, "clear_codes_action"))
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

    def _ensure_connected(self) -> bool:
        if not self.state.active_scanner():
            QMessageBox.warning(self, "Diagnose", "No vehicle connected.")
            return False
        return True

    def _set_busy(self, busy: bool) -> None:
        for btn in (self.full_scan_btn, self.read_codes_btn, self.readiness_btn, self.freeze_btn):
            btn.setEnabled(not busy)
        for btn in (self.quick_clear_btn,):
            btn.setEnabled(not busy)
        for btn in (self.lookup_btn,):
            btn.setEnabled(not busy)
        self.status_label.setText("Working..." if busy else "")
        self.loading_bar.setVisible(busy)

    def _run_full_scan(self) -> None:
        self._run_job(self._job_full_scan, gui_t(self.state, "full_scan"))

    def _run_clear_codes(self) -> None:
        title = gui_t(self.state, "confirm_clear_title")
        body = gui_t(self.state, "confirm_clear_body")
        confirm = QMessageBox.question(self, title, body, QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return
        self._run_job(self._job_clear_codes, gui_t(self.state, "clear_codes_action"))

    def _run_job(self, job: Callable[[], str], label: str) -> None:
        if not self._ensure_connected():
            return
        self._pending_label = label
        self._set_busy(True)
        worker = Worker(job)
        worker.signals.finished.connect(self._on_job_done)
        self.thread_pool.start(worker)

    def _lookup_code(self) -> None:
        code = self.lookup_input.text().strip().upper()
        self.lookup_input.setText(code)
        self.lookup_error.setText("")
        if not code:
            self.lookup_error.setText(gui_t(self.state, "code_missing"))
            self.lookup_result_body.setText(gui_t(self.state, "code_hint"))
            return
        if not re.match(r"^[PBUC][0-3][0-9A-F]{3}$", code):
            self.lookup_error.setText(gui_t(self.state, "code_invalid"))
            self.lookup_result_body.setText(gui_t(self.state, "code_hint"))
            return
        dtc_db = self.state.ensure_dtc_db()
        info = dtc_db.lookup(code)
        if not info:
            self.lookup_result_body.setText(f"{code}: not found in library.")
            self._set_output_text(f"Code {code} not found in library.")
            return
        details = [f"{code} — {info.description}"]
        if info.system:
            details.append(f"System: {info.system}")
        if info.subsystem:
            details.append(f"Subsystem: {info.subsystem}")
        self.lookup_result_body.setText(" | ".join(details))
        lines = []
        lines.extend(_header_lines("CODE LOOKUP"))
        lines.append(f"  Code: {code}")
        lines.append(f"  Description: {info.description}")
        if info.system:
            lines.append(f"  System: {info.system}")
        if info.subsystem:
            lines.append(f"  Subsystem: {info.subsystem}")
        self._set_output_text("\n".join(lines))

    def _clear_lookup(self) -> None:
        self.lookup_input.clear()
        self.lookup_error.setText("")
        self.lookup_result_body.setText(gui_t(self.state, "code_hint"))

    def _search_codes(self) -> None:
        query = self.search_input.text().strip()
        self.search_results.clear()
        if not query:
            self.search_results.addItem(gui_t(self.state, "search_prompt"))
            return
        dtc_db = self.state.ensure_dtc_db()
        results = dtc_db.search(query)
        if not results:
            self.search_results.addItem(gui_t(self.state, "search_none"))
            return
        for info in results[:20]:
            item = QListWidgetItem(f"{info.code}: {info.description}")
            self.search_results.addItem(item)
        if len(results) > 20:
            self.search_results.addItem(f"... +{len(results) - 20} more")

    def _handle_action(self) -> None:
        if not self._ensure_connected():
            return
        sender = self.sender()
        if sender == self.full_scan_btn:
            job = self._job_full_scan
            label = gui_t(self.state, "full_scan")
        elif sender == self.read_codes_btn:
            job = self._job_read_codes
            label = gui_t(self.state, "read_codes")
        elif sender == self.readiness_btn:
            job = self._job_readiness
            label = gui_t(self.state, "readiness")
        else:
            job = self._job_freeze_frame
            label = gui_t(self.state, "freeze_frame")
        self._run_job(job, label)

    def _on_job_done(self, result: Any, err: Any) -> None:
        self._set_busy(False)
        if err:
            QMessageBox.warning(self, "Diagnose", f"Failed: {err}")
            return
        if isinstance(result, str):
            self._set_output_text(result)
            self.last_output = result.splitlines()
            self._store_session_result(self._pending_label or "Scan", result)
        self._pending_label = None

    def _store_session_result(self, label: str, output: str) -> None:
        entry = {
            "title": label,
            "output": output,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        self.state.session_results = [entry]

    def _set_output_text(self, text: str) -> None:
        self.output.setPlainText(text)
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def _clear_output(self) -> None:
        self.output.clear()
        self.last_output = []
        self._pending_label = None

    def _copy_output(self) -> None:
        QApplication.clipboard().setText(self.output.toPlainText())

    def _job_full_scan(self) -> str:
        scanner = self.state.active_scanner()
        if not scanner:
            raise NotConnectedError("Not connected")
        lines: List[str] = []
        lines.extend(_header_lines("FULL DIAGNOSTIC SCAN"))
        lines.append("")
        lines.append(f"  🕐 Report time: {cr_timestamp()}")
        lines.append("")
        info = get_vm().scan_vm.get_vehicle_info()
        lines.extend(_subheader_lines("Vehicle connection"))
        lines.append(f"  ELM Version: {info.get('elm_version', 'unknown')}")
        lines.append(f"  Protocol: {info.get('protocol', 'unknown')}")
        lines.append(f"  MIL Status: {info.get('mil_on', 'unknown')}")
        lines.append(f"  DTC Count: {info.get('dtc_count', 'unknown')}")
        lines.append("")

        lines.extend(_subheader_lines("TROUBLE CODES"))
        dtcs = get_vm().scan_vm.read_dtcs()
        if dtcs:
            for dtc in dtcs:
                status = f" ({dtc.status})" if dtc.status != "stored" else ""
                lines.append(f"  {dtc.code}{status}: {dtc.description}")
        else:
            lines.append("  ✅ No trouble codes found.")
        lines.append("")

        lines.extend(_subheader_lines("READINESS MONITORS"))
        readiness = get_vm().scan_vm.read_readiness()
        if readiness:
            for name, status in readiness.items():
                lines.append(f"  {name}: {status.status_str}")
        else:
            lines.append("  Readiness data unavailable.")
        lines.append("")

        lines.extend(_subheader_lines("LIVE DATA"))
        readings = get_vm().scan_vm.read_live_data()
        if readings:
            for reading in readings.values():
                lines.append(f"  {reading.name}: {reading.value} {reading.unit}")
        else:
            lines.append("  Live data not available.")

        lines.append("")
        lines.append("=" * 60)
        lines.append(f"  Report time: {cr_timestamp()}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def _job_read_codes(self) -> str:
        scanner = self.state.active_scanner()
        if not scanner:
            raise NotConnectedError("Not connected")
        dtcs = get_vm().scan_vm.read_dtcs()
        lines = []
        lines.extend(_header_lines("TROUBLE CODES"))
        lines.append(f"  Time: {cr_timestamp()}")
        lines.append("")
        if dtcs:
            for dtc in dtcs:
                status = f" [{dtc.status}]" if dtc.status != "stored" else ""
                lines.append(f"  {dtc.code}{status}: {dtc.description}")
        else:
            lines.append("  ✅ No trouble codes found.")
        return "\n".join(lines)

    def _job_readiness(self) -> str:
        scanner = self.state.active_scanner()
        if not scanner:
            raise NotConnectedError("Not connected")
        readiness = get_vm().scan_vm.read_readiness()
        lines = []
        lines.extend(_header_lines("READINESS MONITORS"))
        lines.append(f"  Time: {cr_timestamp()}")
        lines.append("")
        if not readiness:
            lines.append("  Readiness data unavailable.")
            return "\n".join(lines)
        for name, status in readiness.items():
            lines.append(f"  {name}: {status.status_str}")
        return "\n".join(lines)

    def _job_freeze_frame(self) -> str:
        scanner = self.state.active_scanner()
        if not scanner:
            raise NotConnectedError("Not connected")
        freeze = get_vm().scan_vm.read_freeze_frame()
        lines = []
        lines.extend(_header_lines("FREEZE FRAME DATA"))
        lines.append(f"  Time: {cr_timestamp()}")
        lines.append("")
        if freeze:
            lines.append(f"  DTC: {freeze.dtc_code}")
            for reading in freeze.readings.values():
                lines.append(f"  {reading.name}: {reading.value} {reading.unit}")
        else:
            lines.append("  No freeze frame data available.")
            lines.append("  (Freeze frames are captured when a DTC is stored)")
        return "\n".join(lines)

    def _job_clear_codes(self) -> str:
        scanner = self.state.active_scanner()
        if not scanner:
            raise NotConnectedError("Not connected")
        lines = []
        lines.extend(_header_lines("CLEAR CODES"))
        lines.append(f"  Time: {cr_timestamp()}")
        lines.append("")
        ok = get_vm().scan_vm.clear_codes()
        if ok:
            lines.append("  ✅ Codes cleared successfully.")
        else:
            lines.append("  ⚠️ Failed to clear codes.")
        return "\n".join(lines)


class LiveDataPage(QWidget):
    def __init__(self, state: AppState, on_back: Callable[[], None], on_reconnect: Callable[[], None]) -> None:
        super().__init__()
        self.state = state
        self.on_back = on_back
        self.on_reconnect = on_reconnect
        self._uses_internal_scroll = True
        self.thread_pool = QThreadPool.globalInstance()
        self.timer = QTimer()
        self.timer.timeout.connect(self._schedule_poll)
        self.poll_in_flight = False
        self.logger = None

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

        title = QLabel(gui_t(self.state, "live_title"))
        title.setObjectName("title")
        content_layout.addWidget(title)

        controls = QHBoxLayout()
        self.start_btn = QPushButton(gui_t(self.state, "start"))
        self.start_btn.setObjectName("primary")
        self.stop_btn = QPushButton(gui_t(self.state, "stop"))
        self.stop_btn.setObjectName("secondary")
        self.stop_btn.setEnabled(False)
        self.customize_btn = QPushButton(gui_t(self.state, "customize"))
        self.customize_btn.setObjectName("secondary")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 10)
        self.interval_spin.setValue(int(self.state.monitor_interval))
        self.interval_spin.setMinimumWidth(96)
        controls.addWidget(self.start_btn)
        controls.addWidget(self.stop_btn)
        self.interval_label = QLabel(gui_t(self.state, "interval"))
        controls.addWidget(self.interval_label)
        controls.addWidget(self.interval_spin)
        controls.addWidget(self.customize_btn)
        controls.addStretch(1)
        self.start_btn.clicked.connect(self._start)
        self.stop_btn.clicked.connect(self._stop)
        self.customize_btn.clicked.connect(self._customize)

        self.status_label = QLabel("")
        self.status_label.setObjectName("hint")

        controls_panel, controls_layout = panel_layout(padding=16)
        controls_panel.setMaximumWidth(PAGE_MAX_WIDTH)
        controls_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        controls_layout.addLayout(controls)
        controls_layout.addWidget(self.status_label)
        content_layout.addWidget(controls_panel)

        self.section_label = QLabel(gui_t(self.state, "telemetry_overview"))
        self.section_label.setObjectName("sectionTitle")

        self.all_metrics = [
            ("05", "Coolant Temp", "°C", 0, 130),
            ("0C", "RPM", "rpm", 0, 6000),
            ("0D", "Speed", "km/h", 0, 200),
            ("11", "Throttle", "%", 0, 100),
            ("49", "Pedal", "%", 0, 100),
            ("42", "Voltage", "V", 0, 16),
        ]
        self.metric_icons = {
            "05": "🌡️",
            "0C": "🧭",
            "0D": "🚗",
            "11": "⚙️",
            "49": "🦶",
            "42": "🔋",
        }
        self.selected_pids = {pid for pid, *_ in self.all_metrics}
        self.cards: Dict[str, Dict[str, Any]] = {}
        self.grid = QGridLayout()
        self.grid.setSpacing(12)

        cards_panel, cards_layout = panel_layout(padding=16)
        cards_panel.setMaximumWidth(PAGE_MAX_WIDTH)
        cards_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        cards_layout.addWidget(self.section_label)
        cards_layout.addLayout(self.grid)
        content_layout.addWidget(cards_panel)

        self.rpm_chart = ChartPanel("Engine RPM")
        self.speed_chart = ChartPanel("Vehicle Speed")
        self.throttle_chart = ChartPanel("Throttle Position")
        self.rpm_chart.setMinimumHeight(180)
        self.speed_chart.setMinimumHeight(180)
        self.throttle_chart.setMinimumHeight(180)
        self.chart_panels = [self.rpm_chart, self.speed_chart, self.throttle_chart]
        self.charts_container = QWidget()
        self.charts_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.charts_grid = QGridLayout(self.charts_container)
        self.charts_grid.setSpacing(12)

        charts_panel, charts_layout = panel_layout(padding=16)
        charts_panel.setMaximumWidth(PAGE_MAX_WIDTH)
        charts_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.charts_title = QLabel(gui_t(self.state, "telemetry_trends"))
        self.charts_title.setObjectName("sectionTitle")
        self.charts_hint = QLabel(gui_t(self.state, "telemetry_trends_hint"))
        self.charts_hint.setObjectName("hint")
        self.trends_placeholder = QLabel(gui_t(self.state, "telemetry_trends_placeholder"))
        self.trends_placeholder.setObjectName("hint")
        self.trends_placeholder.setAlignment(Qt.AlignCenter)
        self.trends_placeholder.setMinimumHeight(120)
        charts_layout.addWidget(self.charts_title)
        charts_layout.addWidget(self.charts_hint)
        charts_layout.addWidget(self.trends_placeholder)
        charts_layout.addWidget(self.charts_container)
        content_layout.addWidget(charts_panel)
        self.charts_panel = charts_panel

        self._build_cards()
        self._layout_charts(self._chart_columns_for_width(self.width()))
        self._update_trends_visibility()

        bottom_row = QHBoxLayout()
        reconnect_btn = QPushButton(gui_t(self.state, "reconnect"))
        reconnect_btn.setObjectName("secondary")
        reconnect_btn.clicked.connect(self.on_reconnect)
        back_btn = QPushButton(gui_t(self.state, "back"))
        back_btn.setObjectName("primary")
        back_btn.clicked.connect(self.on_back)
        bottom_row.addWidget(reconnect_btn)
        bottom_row.addStretch(1)
        bottom_row.addWidget(back_btn)
        content_layout.addLayout(bottom_row)

        self.title = title
        self.reconnect_btn = reconnect_btn
        self.back_btn = back_btn

    def refresh_text(self) -> None:
        self.title.setText(gui_t(self.state, "live_title"))
        self.start_btn.setText(gui_t(self.state, "start"))
        self.stop_btn.setText(gui_t(self.state, "stop"))
        self.interval_label.setText(gui_t(self.state, "interval"))
        self.customize_btn.setText(gui_t(self.state, "customize"))
        self.section_label.setText(gui_t(self.state, "telemetry_overview"))
        self.charts_title.setText(gui_t(self.state, "telemetry_trends"))
        self.charts_hint.setText(gui_t(self.state, "telemetry_trends_hint"))
        self.trends_placeholder.setText(gui_t(self.state, "telemetry_trends_placeholder"))
        self.reconnect_btn.setText(gui_t(self.state, "reconnect"))
        self.back_btn.setText(gui_t(self.state, "back"))

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._layout_charts(self._chart_columns_for_width(self.width()))

    def _ensure_connected(self) -> bool:
        if not self.state.active_scanner():
            QMessageBox.warning(self, "Live Data", "No vehicle connected.")
            return False
        return True

    def _build_cards(self) -> None:
        # Clear grid
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self.cards = {}
        visible = [m for m in self.all_metrics if m[0] in self.selected_pids]
        for idx, (pid, name, unit, _, _) in enumerate(visible):
            card = QFrame()
            card.setObjectName("card")
            apply_shadow(card, blur=16, y=5)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(6)
            card.setMinimumHeight(170)
            card.setMinimumWidth(190)
            value_row = QHBoxLayout()
            icon_label = QLabel(self.metric_icons.get(pid, ""))
            icon_label.setStyleSheet("font-size: 20px;")
            value = QLabel("---")
            value.setObjectName("cardValue")
            unit_label = QLabel(unit)
            unit_label.setObjectName("hint")
            value_row.addWidget(icon_label)
            value_row.addWidget(value)
            value_row.addWidget(unit_label)
            value_row.addStretch(1)
            title = QLabel(name)
            title.setObjectName("cardTitle")
            trend_label = QLabel("—")
            trend_label.setObjectName("hint")
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setObjectName("telemetryBar")
            bar.setTextVisible(True)
            bar.setFormat("—")
            spark = Sparkline()
            gauge = None
            if pid in {"0C", "0D"}:
                gauge = Gauge(min_value=0, max_value=6000 if pid == "0C" else 200)
            card_layout.addLayout(value_row)
            card_layout.addWidget(title)
            card_layout.addWidget(trend_label)
            if gauge:
                card_layout.addWidget(gauge)
            else:
                card_layout.addWidget(bar)
            card_layout.addWidget(spark)
            row, col = divmod(idx, 3)
            self.grid.addWidget(card, row, col)
            self.cards[pid] = {
                "value": value,
                "unit": unit_label,
                "bar": bar,
                "unit_text": unit,
                "spark": spark,
                "gauge": gauge,
                "trend": trend_label,
                "min": None,
                "max": None,
                "last": None,
            }

        # Hide charts if key metrics not selected
        self.rpm_chart.setVisible("0C" in self.selected_pids)
        self.speed_chart.setVisible("0D" in self.selected_pids)
        self.throttle_chart.setVisible("11" in self.selected_pids)
        self._layout_charts(self._chart_columns_for_width(self.width()))

    def _chart_columns_for_width(self, width: int) -> int:
        if width >= 1100:
            return 3
        if width >= 820:
            return 2
        return 1

    def _layout_charts(self, columns: int) -> None:
        if not hasattr(self, "charts_grid"):
            return
        if columns < 1:
            columns = 1
        while self.charts_grid.count():
            item = self.charts_grid.takeAt(0)
            if item.widget():
                item.widget().setParent(self.charts_panel)
        visible = [panel for panel in self.chart_panels if panel.isVisible()]
        for idx, panel in enumerate(visible):
            row, col = divmod(idx, columns)
            self.charts_grid.addWidget(panel, row, col)
        for col in range(columns):
            self.charts_grid.setColumnStretch(col, 1)

    def _update_trends_visibility(self) -> None:
        running = self.timer.isActive()
        self.charts_hint.setVisible(running)
        self.trends_placeholder.setVisible(not running)
        self.charts_container.setVisible(running)

    def _customize(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Telemetry Dashboard")
        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.addWidget(QLabel("Select metrics to display"))
        checks: Dict[str, QCheckBox] = {}
        for pid, name, _, _, _ in self.all_metrics:
            cb = QCheckBox(name)
            cb.setChecked(pid in self.selected_pids)
            checks[pid] = cb
            dlg_layout.addWidget(cb)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dlg_layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() == QDialog.Accepted:
            self.selected_pids = {pid for pid, cb in checks.items() if cb.isChecked()}
            if not self.selected_pids:
                self.selected_pids = {pid for pid, *_ in self.all_metrics}
            self._build_cards()

    def _start(self) -> None:
        if not self._ensure_connected():
            return
        self.state.monitor_interval = float(self.interval_spin.value())
        self.timer.setInterval(int(self.state.monitor_interval * 1000))
        self.timer.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("Live telemetry running...")
        self._update_trends_visibility()
        self._schedule_poll()

    def _stop(self) -> None:
        self.timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("")
        self._update_trends_visibility()
        self.logger = None

    def _schedule_poll(self) -> None:
        if self.poll_in_flight:
            return
        self.poll_in_flight = True
        worker = Worker(self._poll_job)
        worker.signals.finished.connect(self._on_poll_done)
        self.thread_pool.start(worker)

    def _poll_job(self) -> Dict[str, Any]:
        scanner = self.state.active_scanner()
        if not scanner:
            raise NotConnectedError("Not connected")
        pids = list(self.selected_pids)
        return get_vm().scan_vm.read_live_data(pids)

    def _on_poll_done(self, result: Any, err: Any) -> None:
        self.poll_in_flight = False
        if err:
            QMessageBox.warning(self, "Live Data", f"{err}")
            self._stop()
            return
        readings = result or {}
        if self.logger:
            self.logger.log_readings(readings)
        for pid, _, _, min_val, max_val in self.all_metrics:
            widgets = self.cards.get(pid)
            if not widgets:
                continue
            reading = readings.get(pid)
            if reading:
                raw_val = reading.value
                if isinstance(raw_val, (int, float)):
                    value = f"{raw_val:.1f}"
                    pct = 0
                    if max_val > min_val:
                        pct = int(max(0, min(100, (raw_val - min_val) / (max_val - min_val) * 100)))
                    widgets["bar"].setValue(pct)
                    unit = reading.unit or widgets["unit_text"]
                    widgets["bar"].setFormat(f"{value} {unit}")
                    widgets["spark"].add_point(raw_val)
                    if widgets.get("gauge"):
                        widgets["gauge"].set_value(raw_val)
                    if pid == "0C":
                        self.rpm_chart.add_point(raw_val)
                    if pid == "0D":
                        self.speed_chart.add_point(raw_val)
                    if pid == "11":
                        self.throttle_chart.add_point(raw_val)
                    # min/max + trend
                    prev = widgets.get("last")
                    widgets["min"] = raw_val if widgets.get("min") is None else min(widgets["min"], raw_val)
                    widgets["max"] = raw_val if widgets.get("max") is None else max(widgets["max"], raw_val)
                    if prev is None:
                        trend = "→"
                    elif raw_val > prev + 0.1:
                        trend = "▲"
                    elif raw_val < prev - 0.1:
                        trend = "▼"
                    else:
                        trend = "→"
                    widgets["trend"].setText(
                        f"{trend} min {widgets['min']:.1f} / max {widgets['max']:.1f}"
                    )
                    widgets["last"] = raw_val
                else:
                    value = str(raw_val)
                    widgets["bar"].setValue(0)
                    widgets["bar"].setFormat(value)
                widgets["value"].setText(value)
                widgets["unit"].setText(reading.unit or widgets["unit_text"])
            else:
                widgets["value"].setText("---")
                widgets["bar"].setValue(0)
                widgets["bar"].setFormat("—")


class AIReportPage(QWidget):
    def __init__(self, state: AppState, on_back: Callable[[], None], on_reconnect: Callable[[], None]) -> None:
        super().__init__()
        self.state = state
        self.on_back = on_back
        self.on_reconnect = on_reconnect
        self.thread_pool = QThreadPool.globalInstance()
        self.current_report_path = None

        layout = QVBoxLayout(self)
        title = QLabel(gui_t(self.state, "ai_title"))
        title.setObjectName("title")
        layout.addWidget(title)

        credits_row = QHBoxLayout()
        self.credits_label = QLabel("")
        refresh_btn = QPushButton(gui_t(self.state, "refresh_credits"))
        refresh_btn.clicked.connect(self._refresh_balance)
        manage_btn = QPushButton(gui_t(self.state, "manage_credits"))
        manage_btn.clicked.connect(self._open_paywall)
        credits_row.addWidget(self.credits_label)
        credits_row.addStretch(1)
        credits_row.addWidget(refresh_btn)
        credits_row.addWidget(manage_btn)

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
        self.generate_btn.clicked.connect(self._generate_report)
        options_row.addWidget(self.use_vin_decode)
        options_row.addStretch(1)
        options_row.addWidget(self.generate_btn)

        self.status_label = QLabel("")
        self.status_label.setObjectName("hint")

        credits_card = QFrame()
        credits_card.setObjectName("card")
        apply_shadow(credits_card, blur=14, y=4)
        credits_layout = QHBoxLayout(credits_card)
        credits_layout.setContentsMargins(12, 10, 12, 10)
        credits_title = QLabel(gui_t(self.state, "credits_card"))
        credits_title.setObjectName("sectionTitle")
        buy_btn = QPushButton(gui_t(self.state, "buy_credits"))
        buy_btn.setObjectName("primary")
        buy_btn.clicked.connect(self._open_paywall)
        credits_layout.addWidget(credits_title)
        credits_layout.addStretch(1)
        credits_layout.addWidget(buy_btn)

        top_panel, top_layout = panel_layout(padding=16)
        top_panel.setMaximumWidth(PAGE_MAX_WIDTH)
        top_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        top_layout.addLayout(credits_row)
        top_layout.addWidget(credits_card)
        top_layout.addWidget(self.notes_label)
        top_layout.addWidget(self.notes)
        top_layout.addLayout(options_row)
        top_layout.addWidget(self.status_label)
        layout.addWidget(top_panel)

        list_panel, list_layout = panel_layout(padding=14)
        list_panel.setMinimumWidth(320)
        self.reports_label = QLabel(gui_t(self.state, "reports_title"))
        list_layout.addWidget(self.reports_label)
        retention_note = QLabel("PDFs are stored locally. If deleted, regeneration requires credits.")
        retention_note.setObjectName("hint")
        list_layout.addWidget(retention_note)
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(gui_t(self.state, "search_reports"))
        self.search_input.setMinimumWidth(240)
        self.search_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_input.textChanged.connect(self._refresh_reports)
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "complete", "pending", "error"])
        self.status_filter.setMinimumWidth(130)
        self.status_filter.currentIndexChanged.connect(self._refresh_reports)
        self.date_filter = QComboBox()
        self.date_filter.addItems(["All", "Today", "Last 7 days", "Last 30 days"])
        self.date_filter.setMinimumWidth(150)
        self.date_filter.currentIndexChanged.connect(self._refresh_reports)
        self.favorite_btn = QPushButton(gui_t(self.state, "favorite"))
        self.favorite_btn.setObjectName("secondary")
        self.favorite_btn.setMinimumWidth(120)
        self.favorite_btn.clicked.connect(self._toggle_favorite)
        filter_row.addWidget(self.search_input)
        filter_row.addWidget(self.status_filter)
        filter_row.addWidget(self.date_filter)
        filter_row.addWidget(self.favorite_btn)
        list_layout.addLayout(filter_row)
        self.report_list = QListWidget()
        self.report_list.itemSelectionChanged.connect(self._load_selected_report)
        list_layout.addWidget(self.report_list)
        list_btn_row = QHBoxLayout()
        list_btn_row.setSpacing(8)
        refresh_list_btn = QPushButton(gui_t(self.state, "refresh"))
        refresh_list_btn.clicked.connect(self._refresh_reports)
        export_btn = QPushButton(gui_t(self.state, "export"))
        export_btn.clicked.connect(self._export_pdf)
        view_btn = QPushButton(gui_t(self.state, "viewer"))
        view_btn.clicked.connect(self._open_viewer)
        list_btn_row.addWidget(refresh_list_btn)
        list_btn_row.addWidget(export_btn)
        list_btn_row.addWidget(view_btn)
        list_layout.addLayout(list_btn_row)

        preview_panel, preview_layout = panel_layout(padding=14)
        self.preview_label = QLabel(gui_t(self.state, "preview"))
        self.preview_label.setObjectName("sectionTitle")
        preview_layout.addWidget(self.preview_label)
        self.preview_meta = QLabel("")
        self.preview_meta.setObjectName("hint")
        preview_layout.addWidget(self.preview_meta)
        self.chips_row = QHBoxLayout()
        self.dtc_chip = QLabel("DTCs: —")
        self.dtc_chip.setObjectName("chip")
        self.readiness_chip = QLabel("Readiness: —")
        self.readiness_chip.setObjectName("chip")
        self.chips_row.addWidget(self.dtc_chip)
        self.chips_row.addWidget(self.readiness_chip)
        self.chips_row.addStretch(1)
        preview_layout.addLayout(self.chips_row)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        preview_layout.addWidget(self.preview)
        preview_actions = QHBoxLayout()
        self.copy_report_btn = QPushButton(gui_t(self.state, "copy_report"))
        self.copy_report_btn.setObjectName("secondary")
        self.copy_report_btn.clicked.connect(self._copy_report)
        preview_actions.addWidget(self.copy_report_btn)
        preview_actions.addStretch(1)
        preview_layout.addLayout(preview_actions)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(list_panel)
        splitter.addWidget(preview_panel)
        splitter.setSizes([360, 560])
        layout.addWidget(splitter)

        bottom_row = QHBoxLayout()
        reconnect_btn = QPushButton(gui_t(self.state, "reconnect"))
        reconnect_btn.setObjectName("secondary")
        reconnect_btn.clicked.connect(self.on_reconnect)
        back_btn = QPushButton(gui_t(self.state, "back"))
        back_btn.setObjectName("primary")
        back_btn.clicked.connect(self.on_back)
        bottom_row.addWidget(reconnect_btn)
        bottom_row.addStretch(1)
        bottom_row.addWidget(back_btn)
        layout.addLayout(bottom_row)

        self.title = title
        self.refresh_btn = refresh_btn
        self.manage_btn = manage_btn
        self.buy_btn = buy_btn
        self.credits_title = credits_title
        self.refresh_list_btn = refresh_list_btn
        self.export_btn = export_btn
        self.view_btn = view_btn
        self.reconnect_btn = reconnect_btn
        self.back_btn = back_btn
        self.copy_report_btn = self.copy_report_btn

    def refresh_text(self) -> None:
        self.title.setText(gui_t(self.state, "ai_title"))
        self.notes_label.setText(gui_t(self.state, "notes"))
        self.use_vin_decode.setText(gui_t(self.state, "use_vin"))
        self.generate_btn.setText(gui_t(self.state, "generate"))
        self.refresh_btn.setText(gui_t(self.state, "refresh_credits"))
        self.manage_btn.setText(gui_t(self.state, "manage_credits"))
        self.buy_btn.setText(gui_t(self.state, "buy_credits"))
        self.credits_title.setText(gui_t(self.state, "credits_card"))
        self.reports_label.setText(gui_t(self.state, "reports_title"))
        self.refresh_list_btn.setText(gui_t(self.state, "refresh"))
        self.export_btn.setText(gui_t(self.state, "export"))
        self.view_btn.setText(gui_t(self.state, "viewer"))
        self.reconnect_btn.setText(gui_t(self.state, "reconnect"))
        self.back_btn.setText(gui_t(self.state, "back"))
        self.preview_label.setText(gui_t(self.state, "preview"))
        self.search_input.setPlaceholderText(gui_t(self.state, "search_reports"))
        self.favorite_btn.setText(gui_t(self.state, "favorite"))
        self.copy_report_btn.setText(gui_t(self.state, "copy_report"))

        self._refresh_balance()
        self._refresh_reports()

    def _copy_report(self) -> None:
        QApplication.clipboard().setText(self.preview.toPlainText())
        window = self.window()
        if hasattr(window, "show_toast"):
            window.show_toast("Report copied.")

    def _refresh_balance(self) -> None:
        paywall = get_vm().ai_report_vm
        if paywall.is_bypass_enabled():
            self.credits_label.setText("Credits: Superuser bypass enabled")
            return
        if not paywall.is_configured():
            cached = paywall.cached_balance()
            pending = paywall.pending_total()
            if cached:
                self.credits_label.setText(
                    f"Credits (cached): {cached[0]} free / {cached[1]} paid (pending {pending})"
                )
            else:
                self.credits_label.setText("Credits: Paywall not configured")
            return
        self.credits_label.setText("Credits: …")

        def job():
            balance = paywall.get_balance()
            pending = paywall.pending_total()
            return balance, pending

        worker = Worker(job)
        worker.signals.finished.connect(self._refresh_balance_done)
        self.thread_pool.start(worker)

    def _refresh_balance_done(self, result: Optional[Tuple[Any, int]], exc: Optional[Exception]) -> None:
        if exc:
            self.credits_label.setText(f"Credits: Error ({exc})")
            return
        if not result:
            self.credits_label.setText("Credits: -")
            return
        balance, pending = result
        self.credits_label.setText(
            f"Credits: {balance.free_remaining} free / {balance.paid_credits} paid (pending {pending})"
        )

    def _open_paywall(self) -> None:
        dialog = PaywallDialog(self)
        dialog.exec()
        self._refresh_balance()

    def _ensure_connected(self) -> bool:
        if not self.state.active_scanner():
            QMessageBox.warning(self, "AI Report", "No vehicle connected.")
            return False
        return True

    def _refresh_reports(self) -> None:
        self.report_list.clear()
        query = (self.search_input.text() or "").lower().strip()
        status_filter = self.status_filter.currentText()
        date_filter = self.date_filter.currentText()
        now = datetime.now().astimezone()
        for report in get_vm().reports_vm.list_reports():
            if status_filter != "All" and report.status != status_filter:
                continue
            if date_filter != "All":
                try:
                    created = datetime.fromisoformat(report.created_at.replace("Z", "+00:00"))
                except Exception:
                    created = None
                if created:
                    delta_days = (now - created).days
                    if date_filter == "Today" and delta_days != 0:
                        continue
                    if date_filter == "Last 7 days" and delta_days > 7:
                        continue
                    if date_filter == "Last 30 days" and delta_days > 30:
                        continue
            if query and query not in report.report_id.lower():
                # Try match in customer notes (if available)
                try:
                    payload = get_vm().reports_vm.load_report(str(report.file_path))
                except Exception:
                    payload = {}
                notes = str(payload.get("customer_notes", "")).lower()
                if query not in notes:
                    continue
            payload = get_vm().reports_vm.load_report(str(report.file_path))
            fav = "★" if payload.get("favorite") else "☆"
            label = f"{fav} {report.report_id} | {report.created_at} | {report.status}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, report.report_id)
            self.report_list.addItem(item)

    def _load_selected_report(self) -> None:
        item = self.report_list.currentItem()
        if not item:
            return
        report_id = item.data(Qt.UserRole)
        path = get_vm().reports_vm.find_report_by_id(report_id)
        if not path:
            return
        payload = get_vm().reports_vm.load_report(str(path))
        self.current_report_path = path
        text = payload.get("ai_response") or payload.get("ai_response_raw") or ""
        lines: List[str] = []
        lines.extend(_header_lines("AI DIAGNOSTIC REPORT"))
        lines.append(f"  Report ID: {payload.get('report_id', '-')}")
        lines.append(f"  Created: {payload.get('created_at', '-')}")
        lines.append(f"  Status: {payload.get('status', '-')}")
        lines.append(f"  Model: {payload.get('model', '-')}")
        vin_value = ""
        if isinstance(payload.get("vehicle"), dict):
            vin_value = payload.get("vehicle", {}).get("vin") or ""
        if vin_value:
            lines.append(f"  {gui_t(self.state, 'vin_label')}: {vin_value}")
        notes = payload.get("customer_notes", "") or ""
        lines.append("")
        lines.append("  Customer Notes:")
        for line in str(notes).splitlines():
            lines.append(f"    {line}")
        lines.append("")
        lines.append("  AI Response:")
        lines.append("")
        for line in str(text).splitlines():
            lines.append(f"  {line}")
        self.preview.setPlainText("\n".join(lines))
        vehicle = payload.get("vehicle", {}) or {}
        vehicle_label = ", ".join(
            [v for v in [vehicle.get("make"), vehicle.get("model"), vehicle.get("year"), vehicle.get("trim")] if v]
        )
        pdf_path = payload.get("pdf_path") or get_vm().reports_vm.report_pdf_path(
            payload.get("report_id", report_id)
        )
        self.preview_meta.setText(
            f"File: {path.name} | Vehicle: {vehicle_label or '—'} | PDF: {pdf_path}"
        )
        scan_data = payload.get("scan_data") or {}
        dtcs = scan_data.get("dtcs") or []
        readiness = scan_data.get("readiness") or {}
        dtc_count = len(dtcs)
        readiness_complete = 0
        readiness_incomplete = 0
        for _, status in readiness.items():
            if isinstance(status, dict):
                if status.get("available") is False:
                    continue
                if status.get("complete") is True:
                    readiness_complete += 1
                else:
                    readiness_incomplete += 1
        readiness_label = f"{readiness_complete} complete / {readiness_incomplete} incomplete"
        self.dtc_chip.setText(f"DTCs: {dtc_count}")
        self.readiness_chip.setText(f"Readiness: {readiness_label}")

    def _toggle_favorite(self) -> None:
        item = self.report_list.currentItem()
        if not item:
            return
        report_id = item.data(Qt.UserRole)
        path = get_vm().reports_vm.find_report_by_id(report_id)
        if not path:
            return
        payload = get_vm().reports_vm.load_report(str(path))
        payload["favorite"] = not bool(payload.get("favorite"))
        get_vm().reports_vm.write_report(str(path), payload)
        self._refresh_reports()

    def _export_pdf(self) -> None:
        item = self.report_list.currentItem()
        if not item:
            QMessageBox.information(self, "Export", "Select a report first.")
            return
        report_id = item.data(Qt.UserRole)
        path = get_vm().reports_vm.find_report_by_id(report_id)
        if not path:
            QMessageBox.warning(self, "Export", "Report not found.")
            return
        payload = get_vm().reports_vm.load_report(str(path))
        report_json = payload.get("ai_report_json")
        report_text = payload.get("ai_response")
        if not report_json:
            raw_text = payload.get("ai_response_raw") or payload.get("ai_response") or ""
            report_json, parsed_text = extract_report_parts(raw_text)
            if not report_text:
                report_text = parsed_text
        language = payload.get("report_language")
        vehicle_payload = payload.get("vehicle") or {}
        output_path = payload.get("pdf_path")
        if not output_path:
            output_path = _documents_pdf_path(vehicle_payload)
        try:
            get_vm().ai_report_vm.export_pdf(
                payload,
                str(output_path),
                report_json=report_json,
                report_text=report_text,
                language=language,
            )
        except RuntimeError as exc:
            QMessageBox.warning(self, "Export", f"PDF failed: {exc}")
            return
        payload["pdf_path"] = str(output_path)
        get_vm().reports_vm.write_report(str(path), payload)
        window = self.window()
        if hasattr(window, "show_toast"):
            window.show_toast(f"PDF saved: {output_path}")
        else:
            QMessageBox.information(self, "Export", f"PDF saved at:\n{output_path}")

    def _open_viewer(self) -> None:
        item = self.report_list.currentItem()
        if not item:
            QMessageBox.information(self, "Viewer", "Select a report first.")
            return
        report_id = item.data(Qt.UserRole)
        path = get_vm().reports_vm.find_report_by_id(report_id)
        if not path:
            QMessageBox.warning(self, "Viewer", "Report not found.")
            return
        viewer = AIReportViewer(path, self)
        viewer.exec()

    def _generate_report(self) -> None:
        if not self._ensure_connected():
            return
        notes = self.notes.toPlainText().strip()
        if not get_vm().ai_report_vm.is_configured():
            QMessageBox.warning(self, "AI Report", "Missing OPENAI_API_KEY.")
            return
        self.generate_btn.setEnabled(False)
        self.status_label.setText("Generating report...")
        self.loading_bar.setVisible(True)
        worker = Worker(self._generate_job, notes, self.use_vin_decode.isChecked())
        worker.signals.finished.connect(self._on_generate_done)
        self.thread_pool.start(worker)

    def _generate_job(self, notes: str, use_vin_decode: bool) -> Dict[str, Any]:
        scanner = self.state.active_scanner()
        if not scanner:
            raise NotConnectedError("Not connected")
        scan_payload = get_vm().scan_vm.collect_scan_report()
        report_payload = {
            "status": "pending",
            "customer_notes": notes,
            "scan_data": scan_payload,
        }
        report_path = get_vm().reports_vm.save_report(report_payload)

        try:
            vehicle_payload, vehicle_profiles, mismatch = self._prepare_vehicle_payload(
                scan_payload, use_vin_decode
            )
            report_snapshot = get_vm().reports_vm.load_report(str(report_path))
            report_snapshot["vehicle"] = vehicle_payload
            report_snapshot["vehicle_profiles"] = vehicle_profiles
            get_vm().reports_vm.write_report(str(report_path), report_snapshot)
            report_language = detect_report_language(notes, self.state.language)
            report_input = build_report_input(
                scan_payload,
                notes,
                self.state,
                report_language,
                vehicle_payload=vehicle_payload,
                vehicle_profiles=vehicle_profiles,
            )

            paywall = get_vm().ai_report_vm
            if not paywall.is_bypass_enabled():
                if not paywall.is_configured():
                    raise RuntimeError("Paywall API base not configured")
                paywall.consume("generate_report", cost=1)

            response = get_vm().ai_report_vm.request_report(report_input, report_language)
            report_json, report_text = extract_report_parts(response)
            if isinstance(report_json, dict):
                report_language = str(report_json.get("language") or report_language).lower()
            report_language = "es" if str(report_language).lower().startswith("es") else "en"

            update_report_status(
                report_path,
                status="complete",
                response=report_text or response,
                response_raw=response,
                report_json=report_json,
                language=report_language,
                model=get_vm().ai_report_vm.get_model(),
            )
            pdf_path = _documents_pdf_path(vehicle_payload)
            try:
                get_vm().ai_report_vm.export_pdf(
                    get_vm().reports_vm.load_report(str(report_path)),
                    str(pdf_path),
                    report_json=report_json,
                    report_text=report_text or response,
                    language=report_language,
                )
                report_snapshot = get_vm().reports_vm.load_report(str(report_path))
                report_snapshot["pdf_path"] = str(pdf_path)
                get_vm().reports_vm.write_report(str(report_path), report_snapshot)
            except Exception:
                pdf_path = None
            return {
                "path": report_path,
                "text": report_text or response,
                "mismatch": mismatch,
                "vin": vehicle_payload.get("vin"),
                "pdf_path": str(pdf_path) if pdf_path else None,
            }
        except Exception as exc:
            update_report_status(report_path, status="error", error=str(exc))
            raise

    def _on_generate_done(self, result: Any, err: Any) -> None:
        self.generate_btn.setEnabled(True)
        self.status_label.setText("")
        self.loading_bar.setVisible(False)
        if err:
            if isinstance(err, PaymentRequiredError):
                QMessageBox.warning(self, "Paywall", "Payment required to generate report.")
                self._open_paywall()
            else:
                QMessageBox.warning(self, "AI Report", f"Failed: {err}")
            return
        self._refresh_reports()
        if isinstance(result, dict):
            preview_text = result.get("text") or ""
            summary = format_report_summary(preview_text)
            header_lines = _header_lines("AI DIAGNOSTIC REPORT")
            vin_value = result.get("vin")
            if vin_value:
                header_lines.append(f"  {gui_t(self.state, 'vin_label')}: {vin_value}")
                self.state.last_vin = vin_value
            self.preview.setPlainText("\n".join(header_lines) + "\n" + summary)
            if result.get("mismatch"):
                QMessageBox.information(
                    self,
                    "VIN mismatch",
                    "VIN data differs from manual profile. Review vehicle details.",
                )
            if result.get("pdf_path"):
                window = self.window()
                if hasattr(window, "show_toast"):
                    window.show_toast(f"PDF saved at: {result.get('pdf_path')}")
        self._refresh_balance()

    def _prepare_vehicle_payload(
        self, scan_payload: Dict[str, Any], use_vin_decode: bool
    ) -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
        vehicle_info = scan_payload.get("vehicle_info") or {}
        user_profile = self.state.vehicle_profile or {}
        vin = str(vehicle_info.get("vin") or user_profile.get("vin") or "").strip()

        vin_profile: Optional[Dict[str, Any]] = None
        if vin and use_vin_decode:
            cached = get_vm().vin_cache.get(vin)
            if cached:
                vin_profile = cached
            else:
                model_year = user_profile.get("year") or vehicle_info.get("year")
                vin_profile = get_vm().ai_report_vm.decode_vin_vpic(vin, model_year=model_year)
                if vin_profile:
                    get_vm().vin_cache.set(vin, vin_profile)
                if not vin_profile:
                    try:
                        vin_profile = get_vm().ai_report_vm.decode_vin_ai(vin, self.state.manufacturer)
                    except ExternalServiceError:
                        vin_profile = None
                    if vin_profile:
                        get_vm().vin_cache.set(vin, vin_profile)

        def pick(field: str) -> Optional[str]:
            if vin_profile and vin_profile.get(field):
                return vin_profile.get(field)
            if user_profile and user_profile.get(field):
                return user_profile.get(field)
            return vehicle_info.get(field)

        vehicle_payload = {
            "make": pick("make"),
            "model": pick("model"),
            "year": pick("year"),
            "engine": pick("engine"),
            "trim": pick("trim"),
            "vin": vin or vehicle_info.get("vin"),
            "protocol": vehicle_info.get("protocol"),
        }

        mismatch = False
        if vin_profile and user_profile:
            for field in ["make", "model", "year", "trim"]:
                user_val = user_profile.get(field)
                vin_val = vin_profile.get(field)
                if user_val and vin_val and str(user_val).strip().lower() != str(vin_val).strip().lower():
                    mismatch = True
                    break

        profiles = {
            "manual": user_profile or None,
            "vin_decoded": vin_profile or None,
        }
        return vehicle_payload, profiles, mismatch


class UdsToolsPage(QWidget):
    def __init__(self, state: AppState, on_back: Callable[[], None], on_reconnect: Callable[[], None]) -> None:
        super().__init__()
        self.state = state
        self.on_back = on_back
        self.on_reconnect = on_reconnect
        self.thread_pool = QThreadPool.globalInstance()

        layout = QVBoxLayout(self)
        title = QLabel(gui_t(self.state, "uds_title"))
        title.setObjectName("title")
        layout.addWidget(title)

        panel, panel_layout_ = panel_layout()
        panel.setMaximumWidth(PAGE_MAX_WIDTH)
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        form = QFormLayout()
        self.brand_combo = QComboBox()
        self.brand_combo.addItem("Jeep / Chrysler", userData="jeep")
        self.brand_combo.addItem("Land Rover", userData="land_rover")
        if self.state.manufacturer == "landrover":
            self.brand_combo.setCurrentIndex(1)
        form.addRow(gui_t(self.state, "uds_brand"), self.brand_combo)

        self.module_combo = QComboBox()
        form.addRow(gui_t(self.state, "uds_module"), self.module_combo)
        panel_layout_.addLayout(form)

        action_row = QGridLayout()
        action_row.setHorizontalSpacing(10)
        action_row.setVerticalSpacing(8)
        self.read_vin_btn = QPushButton(gui_t(self.state, "uds_read_vin"))
        self.read_vin_btn.setObjectName("secondary")
        self.read_did_btn = QPushButton(gui_t(self.state, "uds_read_did"))
        self.read_did_btn.setObjectName("secondary")
        self.read_dtcs_btn = QPushButton(gui_t(self.state, "uds_read_dtcs"))
        self.read_dtcs_btn.setObjectName("secondary")
        self.send_raw_btn = QPushButton(gui_t(self.state, "uds_send_raw"))
        self.send_raw_btn.setObjectName("secondary")
        action_row.addWidget(self.read_vin_btn, 0, 0)
        action_row.addWidget(self.read_did_btn, 0, 1)
        action_row.addWidget(self.read_dtcs_btn, 1, 0)
        action_row.addWidget(self.send_raw_btn, 1, 1)
        panel_layout_.addLayout(action_row)

        inputs_row = QGridLayout()
        inputs_row.setHorizontalSpacing(10)
        inputs_row.setVerticalSpacing(8)
        self.did_input = QLineEdit()
        self.did_input.setPlaceholderText("F190")
        self.service_input = QLineEdit()
        self.service_input.setPlaceholderText(gui_t(self.state, "uds_service_id"))
        self.data_input = QLineEdit()
        self.data_input.setPlaceholderText(gui_t(self.state, "uds_data_hex"))
        inputs_row.addWidget(QLabel(gui_t(self.state, "uds_read_did")), 0, 0)
        inputs_row.addWidget(self.did_input, 0, 1)
        inputs_row.addWidget(QLabel(gui_t(self.state, "uds_service_id")), 0, 2)
        inputs_row.addWidget(self.service_input, 0, 3)
        inputs_row.addWidget(QLabel(gui_t(self.state, "uds_data_hex")), 1, 0)
        inputs_row.addWidget(self.data_input, 1, 1, 1, 3)
        inputs_row.setColumnStretch(1, 1)
        inputs_row.setColumnStretch(3, 1)
        panel_layout_.addLayout(inputs_row)

        discovery_row = QVBoxLayout()
        discovery_row.setSpacing(8)
        self.discover_btn = QPushButton(gui_t(self.state, "uds_discover"))
        self.discover_btn.setObjectName("secondary")
        self.discover_quick = QCheckBox(gui_t(self.state, "uds_discover_range"))
        self.discover_29 = QCheckBox(gui_t(self.state, "uds_discover_29bit"))
        self.discover_250 = QCheckBox(gui_t(self.state, "uds_discover_250"))
        self.discover_250.setChecked(True)
        self.discover_dtcs = QCheckBox(gui_t(self.state, "uds_discover_dtcs"))
        self.discover_timeout = QSpinBox()
        self.discover_timeout.setRange(50, 1000)
        self.discover_timeout.setValue(120)
        timeout_label = QLabel(gui_t(self.state, "uds_discover_timeout"))
        timeout_row = QHBoxLayout()
        timeout_row.setSpacing(6)
        timeout_row.addWidget(timeout_label)
        timeout_row.addWidget(self.discover_timeout)
        top_row = QHBoxLayout()
        top_row.addWidget(self.discover_btn)
        top_row.addStretch(1)
        top_row.addLayout(timeout_row)
        options_row = QHBoxLayout()
        options_row.setSpacing(10)
        options_row.addWidget(self.discover_quick)
        options_row.addWidget(self.discover_29)
        options_row.addWidget(self.discover_250)
        options_row.addWidget(self.discover_dtcs)
        options_row.addStretch(1)
        discovery_row.addLayout(top_row)
        discovery_row.addLayout(options_row)
        panel_layout_.addLayout(discovery_row)

        hint = QLabel(gui_t(self.state, "uds_discover_hint"))
        hint.setObjectName("subtitle")
        panel_layout_.addWidget(hint)

        cached_row = QHBoxLayout()
        self.cached_label = QLabel("")
        self.cached_label.setObjectName("subtitle")
        self.cached_btn = QPushButton(gui_t(self.state, "uds_discover_cached"))
        self.cached_btn.setObjectName("secondary")
        self.cached_btn.clicked.connect(self._show_cached_map)
        cached_row.addWidget(self.cached_label)
        cached_row.addStretch(1)
        cached_row.addWidget(self.cached_btn)
        panel_layout_.addLayout(cached_row)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(280)
        panel_layout_.addWidget(self.output)
        layout.addWidget(panel)

        bottom_row = QHBoxLayout()
        reconnect_btn = QPushButton(gui_t(self.state, "reconnect"))
        reconnect_btn.setObjectName("secondary")
        reconnect_btn.clicked.connect(self.on_reconnect)
        back_btn = QPushButton(gui_t(self.state, "back"))
        back_btn.setObjectName("primary")
        back_btn.clicked.connect(self.on_back)
        bottom_row.addWidget(reconnect_btn)
        bottom_row.addStretch(1)
        bottom_row.addWidget(back_btn)
        layout.addLayout(bottom_row)
        layout.addStretch(1)

        self.title = title
        self.reconnect_btn = reconnect_btn
        self.back_btn = back_btn
        self.discover_hint = hint

        self.brand_combo.currentIndexChanged.connect(self._refresh_modules)
        self.read_vin_btn.clicked.connect(self._read_vin)
        self.read_did_btn.clicked.connect(self._read_did)
        self.read_dtcs_btn.clicked.connect(self._read_dtcs)
        self.send_raw_btn.clicked.connect(self._send_raw)
        self.discover_btn.clicked.connect(self._discover_modules)
        self._refresh_modules()
        self._refresh_cached_map()

    def refresh_text(self) -> None:
        self.title.setText(gui_t(self.state, "uds_title"))
        self.read_vin_btn.setText(gui_t(self.state, "uds_read_vin"))
        self.read_did_btn.setText(gui_t(self.state, "uds_read_did"))
        self.read_dtcs_btn.setText(gui_t(self.state, "uds_read_dtcs"))
        self.send_raw_btn.setText(gui_t(self.state, "uds_send_raw"))
        self.discover_btn.setText(gui_t(self.state, "uds_discover"))
        self.discover_quick.setText(gui_t(self.state, "uds_discover_range"))
        self.discover_29.setText(gui_t(self.state, "uds_discover_29bit"))
        self.discover_250.setText(gui_t(self.state, "uds_discover_250"))
        self.discover_dtcs.setText(gui_t(self.state, "uds_discover_dtcs"))
        self.discover_hint.setText(gui_t(self.state, "uds_discover_hint"))
        self.cached_btn.setText(gui_t(self.state, "uds_discover_cached"))
        self._refresh_cached_map()
        self.reconnect_btn.setText(gui_t(self.state, "reconnect"))
        self.back_btn.setText(gui_t(self.state, "back"))

    def _refresh_modules(self) -> None:
        brand = self.brand_combo.currentData()
        modules = get_vm().uds_tools.module_map(str(brand))
        self.module_combo.clear()
        cached_map = self._get_cached_map()
        if cached_map:
            cached_modules = cached_map.get("modules") or []
            proto = cached_map.get("protocol") or "6"
            for mod in cached_modules:
                tx = mod.get("tx_id")
                rx = mod.get("rx_id")
                mtype = mod.get("module_type") or ""
                suffix = f" · {mtype}" if mtype else ""
                label = f"[{gui_t(self.state, 'uds_discover_cached_label')}] {tx}->{rx}{suffix}"
                user = {
                    "tx_id": tx,
                    "rx_id": rx,
                    "protocol": proto,
                    "module_type": mod.get("module_type"),
                }
                self.module_combo.addItem(label, userData=user)
        for name in sorted(modules.keys()):
            self.module_combo.addItem(name, userData=name)

    def _refresh_cached_map(self) -> None:
        vin = self.state.last_vin or ""
        cached = get_vm().vin_cache.get(vin) if vin else None
        has_map = bool(cached and cached.get("uds_modules"))
        if vin:
            label = f"{gui_t(self.state, 'uds_discover_cached_label')}: {vin}"
        else:
            label = gui_t(self.state, "uds_discover_cached_none")
        self.cached_label.setText(label)
        self.cached_btn.setEnabled(has_map)

    def _show_cached_map(self) -> None:
        vin = self.state.last_vin or ""
        cached = get_vm().vin_cache.get(vin) if vin else None
        if not cached or not cached.get("uds_modules"):
            QMessageBox.information(self, "UDS", gui_t(self.state, "uds_discover_cached_none"))
            return
        map_payload = cached.get("uds_modules") or {}
        self.output.setPlainText(self._format_cached_result(map_payload))

    def _ensure_connected(self) -> bool:
        if not self.state.active_scanner():
            QMessageBox.warning(self, "UDS", "No vehicle connected.")
            return False
        if self.state.kline_scanner and self.state.kline_scanner.is_connected:
            QMessageBox.warning(self, "UDS", gui_t(self.state, "uds_not_supported"))
            return False
        return True

    def _validate_ready(self) -> Optional[Tuple[str, Any]]:
        if not self._ensure_connected():
            return None
        brand = str(self.brand_combo.currentData() or "jeep")
        module_entry = self.module_combo.currentData()
        if not module_entry:
            QMessageBox.warning(self, "UDS", gui_t(self.state, "uds_no_module"))
            return None
        return brand, module_entry

    def _create_client(self, brand: str, module_entry: Any):
        return get_vm().uds_tools.build_client(brand, module_entry)

    def _get_cached_map(self) -> Optional[Dict[str, Any]]:
        vin = self.state.last_vin or ""
        if not vin:
            return None
        cached = get_vm().vin_cache.get(vin) or {}
        return cached.get("uds_modules")

    def _run_job(self, job: Callable[[], str]) -> None:
        worker = Worker(job)
        worker.signals.finished.connect(self._on_job_done)
        self.thread_pool.start(worker)

    def _on_job_done(self, result: Any, err: Any) -> None:
        if err:
            QMessageBox.warning(self, "UDS", f"{err}")
            return
        if isinstance(result, str):
            self.output.setPlainText(result)
        self._refresh_cached_map()
        self._refresh_modules()

    def _read_vin(self) -> None:
        ready = self._validate_ready()
        if not ready:
            return
        brand, module_entry = ready

        def job() -> str:
            client = self._create_client(brand, module_entry)
            info = client.read_did(brand, "F190")
            lines = _header_lines(gui_t(self.state, "uds_read_vin"))
            lines.append(f"  DID: {info.get('did')}")
            lines.append(f"  Value: {info.get('value')}")
            lines.append(f"  Raw: {info.get('raw')}")
            return "\n".join(lines)

        self._run_job(job)

    def _read_did(self) -> None:
        did = self.did_input.text().strip()
        if not did:
            QMessageBox.information(self, "UDS", gui_t(self.state, "uds_read_did"))
            return
        ready = self._validate_ready()
        if not ready:
            return
        brand, module_entry = ready

        def job() -> str:
            client = self._create_client(brand, module_entry)
            info = client.read_did(brand, did)
            lines = _header_lines(gui_t(self.state, "uds_read_did"))
            lines.append(f"  DID: {info.get('did')}")
            if info.get("name"):
                lines.append(f"  Name: {info.get('name')}")
            lines.append(f"  Value: {info.get('value')}")
            lines.append(f"  Raw: {info.get('raw')}")
            return "\n".join(lines)

        self._run_job(job)

    def _send_raw(self) -> None:
        service_hex = self.service_input.text().strip()
        data_hex = self.data_input.text().strip()
        if not service_hex:
            QMessageBox.information(self, "UDS", gui_t(self.state, "uds_service_id"))
            return
        ready = self._validate_ready()
        if not ready:
            return
        brand, module_entry = ready

        def job() -> str:
            client = self._create_client(brand, module_entry)
            try:
                service_id = int(service_hex, 16)
                data = bytes.fromhex(data_hex) if data_hex else b""
            except ValueError:
                return "Invalid hex input."
            response = client.send_raw(service_id, data)
            lines = _header_lines(gui_t(self.state, "uds_send_raw"))
            lines.append(f"  {gui_t(self.state, 'uds_response')}: {response.hex().upper()}")
            return "\n".join(lines)

        self._run_job(job)

    def _read_dtcs(self) -> None:
        ready = self._validate_ready()
        if not ready:
            return
        brand, module_entry = ready

        def job() -> str:
            client = self._create_client(brand, module_entry)
            response = client.send_raw(0x19, bytes([0x02, 0xFF]), raise_on_negative=True)
            lines = _header_lines(gui_t(self.state, "uds_read_dtcs"))
            if len(response) < 3 or response[0] != 0x59 or response[1] != 0x02:
                lines.append(f"  {gui_t(self.state, 'uds_response')}: {response.hex().upper()}")
                return "\n".join(lines)
            status_mask = response[2]
            payload = response[3:]
            if not payload:
                lines.append(f"  {gui_t(self.state, 'search_none')}")
                return "\n".join(lines)
            lines.append(f"  Status mask: 0x{status_mask:02X}")
            for idx in range(0, len(payload), 4):
                if idx + 4 > len(payload):
                    break
                dtc_bytes = payload[idx : idx + 3]
                status = payload[idx + 3]
                dtc_hex = dtc_bytes.hex().upper()
                lines.append(f"  - 0x{dtc_hex} | status 0x{status:02X}")
            return "\n".join(lines)

        self._run_job(job)

    def _discover_modules(self) -> None:
        if not self._ensure_connected():
            return

        def job() -> str:
            scanner = self.state.active_scanner()
            if not scanner:
                return ""
            id_start, id_end = (0x7E0, 0x7EF) if self.discover_quick.isChecked() else (0x700, 0x7FF)
            options = {
                "id_start": id_start,
                "id_end": id_end,
                "timeout_s": max(0.05, self.discover_timeout.value() / 1000.0),
                "try_250k": self.discover_250.isChecked(),
                "include_29bit": self.discover_29.isChecked(),
                "confirm_vin": True,
                "confirm_dtcs": self.discover_dtcs.isChecked(),
                "brand_hint": self.state.manufacturer,
            }
            result = get_vm().uds_discovery.discover(options)
            return self._format_discovery_result(result)

        self._run_job(job)

    def _format_discovery_result(self, result: Dict[str, Any]) -> str:
        modules = result.get("modules") or []
        if not modules:
            return gui_t(self.state, "uds_discover_none")
        lines = _header_lines(gui_t(self.state, "uds_discover"))
        proto = result.get("protocol") or "?"
        addressing = result.get("addressing") or "?"
        lines.append(f"  {gui_t(self.state, 'uds_discover_found')}: {len(modules)}")
        lines.append(f"  {gui_t(self.state, 'uds_discover_protocol')}: {proto} ({addressing})")
        vin = result.get("vin")
        if vin:
            lines.append(f"  {gui_t(self.state, 'uds_discover_vin')}: {vin}")
        for mod in modules:
            lines.append(f"\n  - TX {mod.tx_id} -> RX {mod.rx_id}")
            if mod.responses:
                lines.append(f"    {gui_t(self.state, 'uds_discover_responses')}: {', '.join(mod.responses)}")
            if mod.alt_tx_ids:
                lines.append(f"    {gui_t(self.state, 'uds_discover_alt_tx')}: {', '.join(mod.alt_tx_ids)}")
            if mod.fingerprint.get('vin'):
                lines.append(f"    VIN: {mod.fingerprint.get('vin')}")
            if mod.module_type:
                lines.append(f"    {gui_t(self.state, 'uds_discover_type')}: {mod.module_type}")
            if mod.fingerprint.get("dtc_summary"):
                summary = mod.fingerprint.get("dtc_summary") or {}
                counts = " ".join(f"{k}:{v}" for k, v in summary.items())
                lines.append(f"    {gui_t(self.state, 'uds_discover_dtcs_summary')}: {counts}")
            if mod.requires_security:
                lines.append(f"    {gui_t(self.state, 'uds_discover_security')}")
            lines.append(f"    {gui_t(self.state, 'uds_discover_confidence')}: {mod.confidence}")
        return "\n".join(lines)

    def _format_cached_result(self, cached: Dict[str, Any]) -> str:
        modules = cached.get("modules") or []
        if not modules:
            return gui_t(self.state, "uds_discover_cached_none")
        lines = _header_lines(gui_t(self.state, "uds_discover_cached"))
        proto = cached.get("protocol") or "?"
        addressing = cached.get("addressing") or "?"
        lines.append(f"  {gui_t(self.state, 'uds_discover_protocol')}: {proto} ({addressing})")
        for mod in modules:
            lines.append(f"\n  - TX {mod.get('tx_id')} -> RX {mod.get('rx_id')}")
            if mod.get("module_type"):
                lines.append(f"    {gui_t(self.state, 'uds_discover_type')}: {mod.get('module_type')}")
            if mod.get("fingerprint", {}).get("dtc_summary"):
                summary = mod.get("fingerprint", {}).get("dtc_summary") or {}
                counts = " ".join(f"{k}:{v}" for k, v in summary.items())
                lines.append(f"    {gui_t(self.state, 'uds_discover_dtcs_summary')}: {counts}")
            if mod.get("responses"):
                lines.append(f"    {gui_t(self.state, 'uds_discover_responses')}: {', '.join(mod.get('responses'))}")
            if mod.get("requires_security"):
                lines.append(f"    {gui_t(self.state, 'uds_discover_security')}")
        return "\n".join(lines)


class ModuleMapPage(QWidget):
    def __init__(self, state: AppState, on_back: Callable[[], None], on_reconnect: Callable[[], None]) -> None:
        super().__init__()
        self.state = state
        self.on_back = on_back
        self.on_reconnect = on_reconnect
        self.thread_pool = QThreadPool.globalInstance()
        self.modules_data: List[Dict[str, Any]] = []
        self.favorites: set[str] = set()

        layout = QVBoxLayout(self)
        title = QLabel(gui_t(self.state, "module_map"))
        title.setObjectName("title")
        layout.addWidget(title)
        hint = QLabel(gui_t(self.state, "module_map_hint"))
        hint.setObjectName("subtitle")
        detail = QLabel(gui_t(self.state, "module_map_hint_detail"))
        detail.setObjectName("hint")
        detail.setWordWrap(True)
        layout.addWidget(hint)
        layout.addWidget(detail)

        panel, panel_layout_ = panel_layout()
        panel.setMaximumWidth(PAGE_MAX_WIDTH)
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        discovery_row = QVBoxLayout()
        discovery_row.setSpacing(8)
        self.discover_btn = QPushButton(gui_t(self.state, "uds_discover"))
        self.discover_btn.setObjectName("primary")
        self.discover_quick = QCheckBox(gui_t(self.state, "uds_discover_range"))
        self.discover_29 = QCheckBox(gui_t(self.state, "uds_discover_29bit"))
        self.discover_250 = QCheckBox(gui_t(self.state, "uds_discover_250"))
        self.discover_250.setChecked(True)
        self.discover_dtcs = QCheckBox(gui_t(self.state, "uds_discover_dtcs"))
        self.discover_timeout = QSpinBox()
        self.discover_timeout.setRange(50, 1000)
        self.discover_timeout.setValue(120)
        timeout_label = QLabel(gui_t(self.state, "uds_discover_timeout"))
        timeout_box = QHBoxLayout()
        timeout_box.setSpacing(6)
        timeout_box.addWidget(timeout_label)
        timeout_box.addWidget(self.discover_timeout)
        top_row = QHBoxLayout()
        top_row.addWidget(self.discover_btn)
        top_row.addStretch(1)
        top_row.addLayout(timeout_box)
        options_row = QHBoxLayout()
        options_row.setSpacing(10)
        options_row.addWidget(self.discover_quick)
        options_row.addWidget(self.discover_29)
        options_row.addWidget(self.discover_250)
        options_row.addWidget(self.discover_dtcs)
        options_row.addStretch(1)
        discovery_row.addLayout(top_row)
        discovery_row.addLayout(options_row)
        panel_layout_.addLayout(discovery_row)

        filter_row = QGridLayout()
        filter_row.setHorizontalSpacing(12)
        filter_row.setVerticalSpacing(10)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(gui_t(self.state, "module_map_search"))
        self.search_input.setMinimumWidth(360)
        self.type_combo = QComboBox()
        self.type_combo.addItem(gui_t(self.state, "module_map_all"))
        self.type_combo.setMinimumWidth(140)
        self.fav_only = QCheckBox(gui_t(self.state, "module_map_favorites"))
        self.security_only = QCheckBox(gui_t(self.state, "module_map_security"))
        filter_row.addWidget(self.search_input, 0, 0, 1, 3)
        filter_row.addWidget(self.type_combo, 0, 3)
        filter_row.addWidget(self.fav_only, 1, 0)
        filter_row.addWidget(self.security_only, 1, 1)
        filter_row.setColumnStretch(2, 1)
        panel_layout_.addLayout(filter_row)

        self.list_area = QScrollArea()
        self.list_area.setWidgetResizable(True)
        self.list_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setSpacing(10)
        self.list_area.setWidget(self.list_container)
        panel_layout_.addWidget(self.list_area)

        layout.addWidget(panel)

        bottom_row = QHBoxLayout()
        reconnect_btn = QPushButton(gui_t(self.state, "reconnect"))
        reconnect_btn.setObjectName("secondary")
        reconnect_btn.clicked.connect(self.on_reconnect)
        back_btn = QPushButton(gui_t(self.state, "back"))
        back_btn.setObjectName("primary")
        back_btn.clicked.connect(self.on_back)
        bottom_row.addWidget(reconnect_btn)
        bottom_row.addStretch(1)
        bottom_row.addWidget(back_btn)
        layout.addLayout(bottom_row)
        layout.addStretch(1)

        self.title = title
        self.hint = hint
        self.detail = detail
        self.reconnect_btn = reconnect_btn
        self.back_btn = back_btn

        self.discover_btn.clicked.connect(self._run_discovery)
        self.search_input.textChanged.connect(lambda _: self._apply_filters())
        self.type_combo.currentIndexChanged.connect(lambda _: self._apply_filters())
        self.fav_only.toggled.connect(lambda _: self._apply_filters())
        self.security_only.toggled.connect(lambda _: self._apply_filters())

        self.refresh_text()
        self.refresh_data()

    def refresh_text(self) -> None:
        self.title.setText(gui_t(self.state, "module_map"))
        self.hint.setText(gui_t(self.state, "module_map_hint"))
        self.detail.setText(gui_t(self.state, "module_map_hint_detail"))
        self.discover_btn.setText(gui_t(self.state, "uds_discover"))
        self.discover_quick.setText(gui_t(self.state, "uds_discover_range"))
        self.discover_29.setText(gui_t(self.state, "uds_discover_29bit"))
        self.discover_250.setText(gui_t(self.state, "uds_discover_250"))
        self.discover_dtcs.setText(gui_t(self.state, "uds_discover_dtcs"))
        self.search_input.setPlaceholderText(gui_t(self.state, "module_map_search"))
        self.fav_only.setText(gui_t(self.state, "module_map_favorites"))
        self.security_only.setText(gui_t(self.state, "module_map_security"))
        self.reconnect_btn.setText(gui_t(self.state, "reconnect"))
        self.back_btn.setText(gui_t(self.state, "back"))

    def refresh_data(self) -> None:
        cached = self._get_cached_map()
        if not cached:
            self.modules_data = []
            self.favorites = set()
        else:
            self.modules_data = cached.get("modules") or []
            favs = cached.get("favorites") or []
            self.favorites = set(favs)
        self._refresh_type_filter()
        self._apply_filters()

    def _refresh_type_filter(self) -> None:
        current = self.type_combo.currentText()
        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        self.type_combo.addItem(gui_t(self.state, "module_map_all"))
        types = sorted({(m.get("module_type") or "Unknown") for m in self.modules_data})
        for t_name in types:
            self.type_combo.addItem(t_name)
        if current:
            idx = self.type_combo.findText(current)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
        self.type_combo.blockSignals(False)

    def _apply_filters(self) -> None:
        query = self.search_input.text().strip().lower()
        type_filter = self.type_combo.currentText()
        if type_filter == gui_t(self.state, "module_map_all"):
            type_filter = ""
        fav_only = self.fav_only.isChecked()
        sec_only = self.security_only.isChecked()

        filtered = []
        for mod in self.modules_data:
            tx = (mod.get("tx_id") or "").lower()
            rx = (mod.get("rx_id") or "").lower()
            mtype = (mod.get("module_type") or "Unknown")
            if type_filter and mtype != type_filter:
                continue
            key = self._module_key(mod)
            if fav_only and key not in self.favorites:
                continue
            if sec_only and not mod.get("requires_security"):
                continue
            blob = f"{tx} {rx} {mtype.lower()}"
            if query and query not in blob:
                continue
            filtered.append(mod)

        self._render_list(filtered)

    def _render_list(self, modules: List[Dict[str, Any]]) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        if not modules:
            empty = QLabel(gui_t(self.state, "uds_discover_none"))
            empty.setObjectName("subtitle")
            self.list_layout.addWidget(empty)
            self.list_layout.addStretch(1)
            return

        for mod in modules:
            card = QFrame()
            card.setObjectName("card")
            card_layout = QHBoxLayout(card)
            left = QVBoxLayout()
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
            tags = []
            addressing = mod.get("addressing")
            if addressing:
                tags.append(addressing)
            if mod.get("protocol"):
                tags.append(f"CAN {mod.get('protocol')}")
            if mod.get("requires_security"):
                tags.append("Security")
            if mod.get("fingerprint", {}).get("vin"):
                tags.append("VIN")
            for tag in tags:
                lbl = QLabel(tag)
                lbl.setObjectName("tag")
                tags_row.addWidget(lbl)
            left.addLayout(tags_row)

            card_layout.addLayout(left)
            card_layout.addStretch(1)

            fav_btn = QPushButton("★" if self._module_key(mod) in self.favorites else "☆")
            fav_btn.setObjectName("secondary")
            fav_btn.setFixedWidth(44)
            fav_btn.clicked.connect(lambda _=False, m=mod, b=fav_btn: self._toggle_favorite(m, b))
            card_layout.addWidget(fav_btn)
            self.list_layout.addWidget(card)

        self.list_layout.addStretch(1)

    def _run_discovery(self) -> None:
        if not self.state.active_scanner():
            QMessageBox.warning(self, "UDS", "No vehicle connected.")
            return

        def job() -> Dict[str, Any]:
            scanner = self.state.active_scanner()
            if not scanner:
                return {}
            id_start, id_end = (0x7E0, 0x7EF) if self.discover_quick.isChecked() else (0x700, 0x7FF)
            options = {
                "id_start": id_start,
                "id_end": id_end,
                "timeout_s": max(0.05, self.discover_timeout.value() / 1000.0),
                "try_250k": self.discover_250.isChecked(),
                "include_29bit": self.discover_29.isChecked(),
                "confirm_vin": True,
                "confirm_dtcs": self.discover_dtcs.isChecked(),
                "brand_hint": self.state.manufacturer,
            }
            return get_vm().uds_discovery.discover(options)

        worker = Worker(job)
        worker.signals.finished.connect(self._on_discovery_done)
        self.thread_pool.start(worker)

    def _on_discovery_done(self, result: Any, err: Any) -> None:
        if err:
            QMessageBox.warning(self, "UDS", f"{err}")
            return
        if not result:
            QMessageBox.information(self, "UDS", gui_t(self.state, "uds_discover_none"))
            return
        self.refresh_data()

    def _toggle_favorite(self, mod: Dict[str, Any], btn: QPushButton) -> None:
        key = self._module_key(mod)
        if key in self.favorites:
            self.favorites.remove(key)
        else:
            self.favorites.add(key)
        btn.setText("★" if key in self.favorites else "☆")
        self._save_favorites()

    def _module_key(self, mod: Dict[str, Any]) -> str:
        return f"{mod.get('tx_id')}->{mod.get('rx_id')}"

    def _save_favorites(self) -> None:
        vin = self.state.last_vin or ""
        if not vin:
            return
        cached = get_vm().vin_cache.get(vin) or {}
        uds_map = cached.get("uds_modules") or {}
        uds_map["favorites"] = sorted(self.favorites)
        cached["uds_modules"] = uds_map
        get_vm().vin_cache.set(vin, cached)

    def _get_cached_map(self) -> Optional[Dict[str, Any]]:
        vin = self.state.last_vin or ""
        if not vin:
            return None
        cached = get_vm().vin_cache.get(vin) or {}
        return cached.get("uds_modules")


class AIReportViewer(QDialog):
    def __init__(self, report_path: Any, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI Report Viewer")
        self.report_path = report_path
        self.payload = get_vm().reports_vm.load_report(str(report_path))

        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        json_panel = QWidget()
        json_layout = QVBoxLayout(json_panel)
        json_layout.addWidget(QLabel("AI JSON"))
        self.json_text = QPlainTextEdit()
        self.json_text.setReadOnly(True)
        json_layout.addWidget(self.json_text)
        splitter.addWidget(json_panel)

        pdf_panel = QWidget()
        pdf_layout = QVBoxLayout(pdf_panel)
        pdf_layout.addWidget(QLabel("PDF Preview"))

        self.pdf_container = QWidget()
        pdf_layout.addWidget(self.pdf_container)
        splitter.addWidget(pdf_panel)

        splitter.setSizes([420, 420])
        layout.addWidget(splitter)

        btn_row = QHBoxLayout()
        open_btn = QPushButton("Open PDF")
        open_btn.clicked.connect(self._open_pdf)
        btn_row.addStretch(1)
        btn_row.addWidget(open_btn)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_content()

    def _load_content(self) -> None:
        report_json = self.payload.get("ai_report_json")
        report_text = self.payload.get("ai_response")
        if not report_json:
            raw_text = self.payload.get("ai_response_raw") or self.payload.get("ai_response") or ""
            report_json, parsed_text = extract_report_parts(raw_text)
            if not report_text:
                report_text = parsed_text
        language = self.payload.get("report_language")

        pretty = json.dumps(report_json or {}, ensure_ascii=False, indent=2)
        self.json_text.setPlainText(pretty)

        pdf_path = self.payload.get("pdf_path")
        if pdf_path:
            self.pdf_path = Path(pdf_path)
        else:
            vehicle_payload = self.payload.get("vehicle") or {}
            self.pdf_path = _documents_pdf_path(vehicle_payload)
        if not self.pdf_path.exists():
            try:
                get_vm().ai_report_vm.export_pdf(
                    self.payload,
                    str(self.pdf_path),
                    report_json=report_json,
                    report_text=report_text,
                    language=language,
                )
                self.payload["pdf_path"] = str(self.pdf_path)
                get_vm().reports_vm.write_report(str(self.report_path), self.payload)
            except RuntimeError as exc:
                QMessageBox.warning(self, "PDF", f"Failed to generate PDF: {exc}")
                return

        self._render_pdf()

    def _render_pdf(self) -> None:
        for child in self.pdf_container.children():
            if isinstance(child, QWidget):
                child.setParent(None)

        if _HAS_PDF_PREVIEW and QPdfDocument and QPdfView:
            doc = QPdfDocument(self)
            doc.load(str(self.pdf_path))
            view = QPdfView()
            view.setDocument(doc)
            layout = QVBoxLayout(self.pdf_container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(view)
            self.pdf_doc = doc
            self.pdf_view = view
        else:
            layout = QVBoxLayout(self.pdf_container)
            layout.setContentsMargins(0, 0, 0, 0)
            label = QLabel("PDF preview not available. Use 'Open PDF'.")
            label.setWordWrap(True)
            layout.addWidget(label)

    def _open_pdf(self) -> None:
        if self.pdf_path:
            webbrowser.open(self.pdf_path.as_uri())


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
        self.copy_full_btn = self.copy_full_btn

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
        meta_lines = [
            f"Title: {title}",
            f"Saved at: {saved_at}",
            f"Vehicle: {vehicle}",
        ]
        self.metadata_text.setPlainText("\n".join(meta_lines))

    def _copy_full_report(self) -> None:
        QApplication.clipboard().setText(self.preview.toPlainText())


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
            QMessageBox.information(self, "Settings", "Settings saved.")

    def _apply_brand_lock(self) -> None:
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

    def _on_brand_change(self) -> None:
        brand_id = self.brand_combo.currentData()
        if isinstance(brand_id, str):
            get_vm().settings_vm.apply_brand_selection(brand_id)
        self._apply_brand_lock()


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
        self.menu_page = MainMenuPage(self.state, self._open_page, self._reconnect)
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
        self._refresh_language()
        self.connect_page.update_empty_state()
        self.shell.update_connection_bar()
        if hasattr(self.menu_page, "refresh_text"):
            self.menu_page.refresh_text()
        if hasattr(self.reports_page, "_refresh"):
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
            QMessageBox.information(self, "Menu", "This section is not wired yet.")

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


def main() -> int:
    init_environment()
    get_vm()
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLES)
    app.setFont(QFontDatabase.systemFont(QFontDatabase.GeneralFont))
    window = MainWindow()
    window.resize(980, 640)
    window.show()
    QTimer.singleShot(0, window.start_timers)
    return app.exec()


def run() -> int:
    return main()
