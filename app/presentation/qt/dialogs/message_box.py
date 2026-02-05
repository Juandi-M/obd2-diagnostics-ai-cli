from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QMessageBox, QWidget


# Avoid QMessageBox static helpers (information/warning/...) because they call
# QDialog.exec() (nested event loop). On macOS + BLE (CoreBluetooth via bleak) we
# observed hard crashes (SIGSEGV) when these modal exec dialogs are shown.
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


def ui_confirm(
    parent: Optional[QWidget],
    title: str,
    text: str,
    *,
    on_yes: Callable[[], None],
    on_no: Optional[Callable[[], None]] = None,
) -> None:
    """Non-blocking Yes/No confirmation (avoids nested event loops)."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    box.setDefaultButton(QMessageBox.StandardButton.Yes)
    box.setWindowModality(Qt.WindowModality.WindowModal if parent else Qt.WindowModality.ApplicationModal)
    box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
    _ACTIVE_MESSAGE_BOXES.append(box)

    def _cleanup(_: int) -> None:
        try:
            _ACTIVE_MESSAGE_BOXES.remove(box)
        except ValueError:
            pass
        box.deleteLater()

    def _clicked(button) -> None:  # type: ignore[no-untyped-def]
        try:
            sb = box.standardButton(button)
        except Exception:
            sb = QMessageBox.StandardButton.NoButton
        if sb == QMessageBox.StandardButton.Yes:
            on_yes()
        elif on_no:
            on_no()

    box.buttonClicked.connect(_clicked)
    box.finished.connect(_cleanup)
    QTimer.singleShot(0, box.open)
