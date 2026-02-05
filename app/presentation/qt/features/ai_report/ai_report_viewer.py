from __future__ import annotations

import json
import webbrowser
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

try:  # Optional PDF preview widgets
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView

    _HAS_PDF_PREVIEW = True
except Exception:  # pragma: no cover - optional dependency
    QPdfDocument = None  # type: ignore[assignment]
    QPdfView = None  # type: ignore[assignment]
    _HAS_PDF_PREVIEW = False

from app.presentation.qt.app_vm import get_vm
from app.presentation.qt.dialogs.message_box import ui_warn
from app.presentation.qt.utils.ai_report import documents_pdf_path, extract_report_parts


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
            self.pdf_path = documents_pdf_path(vehicle_payload)

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
                ui_warn(self, "PDF", f"Failed to generate PDF: {exc}")
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
            return

        layout = QVBoxLayout(self.pdf_container)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel("PDF preview not available. Use 'Open PDF'.")
        label.setWordWrap(True)
        layout.addWidget(label)

    def _open_pdf(self) -> None:
        if getattr(self, "pdf_path", None):
            webbrowser.open(self.pdf_path.as_uri())

