from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from PySide6.QtCore import Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.application.state import AppState
from app.presentation.qt.features.live_data.customize_dialog import choose_metrics
from app.presentation.qt.features.live_data.metrics import ALL_METRICS, METRIC_ICONS
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.style import PAGE_MAX_WIDTH, apply_shadow, panel_layout
from app.presentation.qt.widgets.charts import ChartPanel, Gauge, Sparkline


class LiveDashboard(QWidget):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        self.selected_pids: Set[str] = {pid for pid, *_ in ALL_METRICS}
        self.cards: Dict[str, Dict[str, Any]] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        cards_panel, cards_layout = panel_layout(padding=16)
        cards_panel.setMaximumWidth(PAGE_MAX_WIDTH)
        cards_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.section_label = QLabel(gui_t(self.state, "telemetry_overview"))
        self.section_label.setObjectName("sectionTitle")
        self.grid = QGridLayout()
        self.grid.setSpacing(12)
        cards_layout.addWidget(self.section_label)
        cards_layout.addLayout(self.grid)
        layout.addWidget(cards_panel)

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
        self.charts_container = QWidget()
        self.charts_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.charts_grid = QGridLayout(self.charts_container)
        self.charts_grid.setSpacing(12)

        self.rpm_chart = ChartPanel("Engine RPM")
        self.speed_chart = ChartPanel("Vehicle Speed")
        self.throttle_chart = ChartPanel("Throttle Position")
        for p in (self.rpm_chart, self.speed_chart, self.throttle_chart):
            p.setMinimumHeight(180)
        self.chart_panels = [self.rpm_chart, self.speed_chart, self.throttle_chart]

        charts_layout.addWidget(self.charts_title)
        charts_layout.addWidget(self.charts_hint)
        charts_layout.addWidget(self.trends_placeholder)
        charts_layout.addWidget(self.charts_container)
        layout.addWidget(charts_panel)

        self._build_cards()
        self._layout_charts(self._chart_columns_for_width(self.width()))
        self.set_running(False)

    def refresh_text(self) -> None:
        self.section_label.setText(gui_t(self.state, "telemetry_overview"))
        self.charts_title.setText(gui_t(self.state, "telemetry_trends"))
        self.charts_hint.setText(gui_t(self.state, "telemetry_trends_hint"))
        self.trends_placeholder.setText(gui_t(self.state, "telemetry_trends_placeholder"))

    def pids(self) -> List[str]:
        return list(self.selected_pids)

    def set_running(self, running: bool) -> None:
        self.charts_hint.setVisible(running)
        self.trends_placeholder.setVisible(not running)
        self.charts_container.setVisible(running)

    def customize(self, parent: QWidget) -> None:
        picked = choose_metrics(parent, self.selected_pids)
        if picked is None:
            return
        self.selected_pids = picked or {pid for pid, *_ in ALL_METRICS}
        self._build_cards()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 - Qt naming
        super().resizeEvent(event)
        self._layout_charts(self._chart_columns_for_width(self.width()))

    def _build_cards(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self.cards = {}
        visible = [m for m in ALL_METRICS if m[0] in self.selected_pids]

        for idx, (pid, name, unit, _min, _max) in enumerate(visible):
            card = QFrame()
            card.setObjectName("card")
            apply_shadow(card, blur=16, y=5)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(6)
            card.setMinimumHeight(170)
            card.setMinimumWidth(190)
            value_row = QHBoxLayout()
            icon_label = QLabel(METRIC_ICONS.get(pid, ""))
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
            gauge: Optional[Gauge] = None
            if pid in {"0C", "0D"}:
                gauge = Gauge(min_value=0, max_value=6000 if pid == "0C" else 200)
            card_layout.addLayout(value_row)
            card_layout.addWidget(title)
            card_layout.addWidget(trend_label)
            card_layout.addWidget(gauge if gauge else bar)
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
                "min_val": _min,
                "max_val": _max,
            }

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
        if columns < 1:
            columns = 1
        while self.charts_grid.count():
            item = self.charts_grid.takeAt(0)
            if item.widget():
                item.widget().setParent(self.charts_container)

        visible = [panel for panel in self.chart_panels if panel.isVisible()]
        for idx, panel in enumerate(visible):
            row, col = divmod(idx, columns)
            self.charts_grid.addWidget(panel, row, col)
        for col in range(columns):
            self.charts_grid.setColumnStretch(col, 1)

    def update_readings(self, readings: Dict[str, Any]) -> None:
        for pid, _, _, _min, _max in ALL_METRICS:
            widgets = self.cards.get(pid)
            if not widgets:
                continue
            reading = readings.get(pid)
            if not reading:
                widgets["value"].setText("---")
                widgets["bar"].setValue(0)
                widgets["bar"].setFormat("—")
                continue

            raw_val = getattr(reading, "value", None)
            if isinstance(raw_val, (int, float)):
                value = f"{raw_val:.1f}"
                pct = 0
                max_val = widgets.get("max_val", _max)
                min_val = widgets.get("min_val", _min)
                if max_val > min_val:
                    pct = int(max(0, min(100, (raw_val - min_val) / (max_val - min_val) * 100)))
                widgets["bar"].setValue(pct)
                unit = getattr(reading, "unit", None) or widgets["unit_text"]
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
                widgets["trend"].setText(f"{trend} min {widgets['min']:.1f} / max {widgets['max']:.1f}")
                widgets["last"] = raw_val
            else:
                value = str(raw_val)
                widgets["bar"].setValue(0)
                widgets["bar"].setFormat(value)

            widgets["value"].setText(value)
            widgets["unit"].setText(getattr(reading, "unit", None) or widgets["unit_text"])
