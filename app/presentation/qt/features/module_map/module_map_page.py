from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.application.state import AppState
from app.presentation.qt.app_vm import get_vm
from app.presentation.qt.dialogs.message_box import ui_info, ui_warn
from app.presentation.qt.features.module_map.module_map_cards import build_module_card, module_key
from app.presentation.qt.features.module_map.module_map_view import ModuleMapView
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.workers import Worker


class ModuleMapPage(QWidget):
    def __init__(self, state: AppState, on_back: Callable[[], None], on_reconnect: Callable[[], None]) -> None:
        super().__init__()
        self.state = state
        self.thread_pool = QThreadPool.globalInstance()
        self.modules_data: List[Dict[str, Any]] = []
        self.favorites: set[str] = set()

        self.view = ModuleMapView(self.state, on_back=on_back, on_reconnect=on_reconnect)
        self.view.discover_btn.clicked.connect(self._run_discovery)
        self.view.search_input.textChanged.connect(lambda _: self._apply_filters())
        self.view.type_combo.currentIndexChanged.connect(lambda _: self._apply_filters())
        self.view.fav_only.toggled.connect(lambda _: self._apply_filters())
        self.view.security_only.toggled.connect(lambda _: self._apply_filters())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.view)

        self.refresh_text()
        self.refresh_data()

    def refresh_text(self) -> None:
        self.view.refresh_text()
        self._refresh_type_filter()
        self._apply_filters()

    def refresh_data(self) -> None:
        cached = self._get_cached_map()
        if not cached:
            self.modules_data = []
            self.favorites = set()
        else:
            self.modules_data = cached.get("modules") or []
            self.favorites = set(cached.get("favorites") or [])
        self._refresh_type_filter()
        self._apply_filters()

    def _get_cached_map(self) -> Optional[Dict[str, Any]]:
        vin = self.state.last_vin or ""
        if not vin:
            return None
        cached = get_vm().vin_cache.get(vin) or {}
        return cached.get("uds_modules")

    def _run_discovery(self) -> None:
        if not self.state.active_scanner():
            ui_warn(self, "UDS", "No vehicle connected.")
            return

        def job() -> Dict[str, Any]:
            id_start, id_end = (0x7E0, 0x7EF) if self.view.discover_quick.isChecked() else (0x700, 0x7FF)
            options = {
                "id_start": id_start,
                "id_end": id_end,
                "timeout_s": max(0.05, self.view.discover_timeout.value() / 1000.0),
                "try_250k": self.view.discover_250.isChecked(),
                "include_29bit": self.view.discover_29.isChecked(),
                "confirm_vin": True,
                "confirm_dtcs": self.view.discover_dtcs.isChecked(),
                "brand_hint": self.state.manufacturer,
            }
            return get_vm().uds_discovery.discover(options)

        worker = Worker(job)
        worker.signals.finished.connect(self._on_discovery_done)
        self.thread_pool.start(worker)

    def _on_discovery_done(self, result: Any, err: Any) -> None:
        if err:
            ui_warn(self, "UDS", f"{err}")
            return
        if not result or not (result.get("modules") or []):
            ui_info(self, "UDS", gui_t(self.state, "uds_discover_none"))
        self.refresh_data()

    def _refresh_type_filter(self) -> None:
        current = self.view.type_combo.currentText()
        self.view.type_combo.blockSignals(True)
        self.view.type_combo.clear()
        self.view.type_combo.addItem(gui_t(self.state, "module_map_all"))
        types = sorted({(m.get("module_type") or "Unknown") for m in self.modules_data})
        for t_name in types:
            self.view.type_combo.addItem(t_name)
        if current:
            idx = self.view.type_combo.findText(current)
            if idx >= 0:
                self.view.type_combo.setCurrentIndex(idx)
        self.view.type_combo.blockSignals(False)

    def _apply_filters(self) -> None:
        query = self.view.search_input.text().strip().lower()
        type_filter = self.view.type_combo.currentText()
        if type_filter == gui_t(self.state, "module_map_all"):
            type_filter = ""
        fav_only = self.view.fav_only.isChecked()
        sec_only = self.view.security_only.isChecked()

        filtered: List[Dict[str, Any]] = []
        for mod in self.modules_data:
            tx = (mod.get("tx_id") or "").lower()
            rx = (mod.get("rx_id") or "").lower()
            mtype = (mod.get("module_type") or "Unknown")
            if type_filter and mtype != type_filter:
                continue
            key = module_key(mod)
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
        while self.view.list_layout.count():
            item = self.view.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        if not modules:
            empty = QLabel(gui_t(self.state, "uds_discover_none"))
            empty.setObjectName("subtitle")
            self.view.list_layout.addWidget(empty)
            self.view.list_layout.addStretch(1)
            return

        for mod in modules:
            key = module_key(mod)
            card = build_module_card(mod, favorite=key in self.favorites, on_toggle_favorite=self._toggle_favorite)
            self.view.list_layout.addWidget(card)
        self.view.list_layout.addStretch(1)

    def _toggle_favorite(self, mod: Dict[str, Any], btn) -> None:  # type: ignore[no-untyped-def]
        key = module_key(mod)
        if key in self.favorites:
            self.favorites.remove(key)
        else:
            self.favorites.add(key)
        btn.setText("★" if key in self.favorites else "☆")
        self._save_favorites()

    def _save_favorites(self) -> None:
        vin = self.state.last_vin or ""
        if not vin:
            return
        cached = get_vm().vin_cache.get(vin) or {}
        uds_map = cached.get("uds_modules") or {}
        uds_map["favorites"] = sorted(self.favorites)
        cached["uds_modules"] = uds_map
        get_vm().vin_cache.set(vin, cached)
