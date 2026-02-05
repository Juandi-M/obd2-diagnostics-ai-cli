from __future__ import annotations

import math
from typing import List

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


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

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
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

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
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
            pen_bg.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_bg)
            painter.drawArc(arc_rect, start_angle * 16, sweep_angle * 16)

            # Value arc
            span = self.max_value - self.min_value or 1.0
            pct = max(0.0, min(1.0, (self.value - self.min_value) / span))
            pen_val = QPen(QColor("#2f3a44"), 8)
            pen_val.setCapStyle(Qt.PenCapStyle.RoundCap)
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

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
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
