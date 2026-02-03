from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
from pathlib import Path
from xml.sax.saxutils import escape


SECTION_KEYS = [
    "1_identificacion_vehiculo",
    "2_motivo_visita",
    "3_resultado_escaneo",
    "4_evidencia_datos_en_vivo",
    "5_interpretacion_tecnica",
    "6_causas_probables",
    "7_pruebas_recomendadas",
    "8_acciones_recomendadas",
    "9_notas_limitaciones",
    "10_timestamp",
]

SECTION_TITLES = {
    "es": [
        "1) Identificación del vehículo",
        "2) Motivo de visita / Síntomas reportados",
        "3) Resultado del escaneo (DTCs, MIL, readiness)",
        "4) Evidencia en datos en vivo",
        "5) Interpretación técnica",
        "6) Causas probables (prioridad)",
        "7) Pruebas recomendadas",
        "8) Acciones recomendadas",
        "9) Notas y limitaciones",
        "10) Timestamp",
    ],
    "en": [
        "1) Vehicle identification",
        "2) Reason for visit / reported symptoms",
        "3) Scan results (DTCs, MIL, readiness)",
        "4) Live data evidence",
        "5) Technical interpretation",
        "6) Probable causes (priority)",
        "7) Recommended tests",
        "8) Recommended actions",
        "9) Notes and limitations",
        "10) Timestamp",
    ],
}

META_LABELS = {
    "es": {
        "title": "REPORTE DIAGNÓSTICO OBD-II",
        "pdf_title": "Reporte Diagnóstico OBD-II",
        "report_id": "Reporte ID",
        "created": "Creado",
        "status": "Estado",
        "model": "Modelo",
        "vin": "VIN",
        "not_specified": "No especificado",
        "not_available": "No disponible",
        "report_text": "Reporte (texto)",
        "report_unavailable": "Reporte no disponible.",
        "criteria": "Criterio",
    },
    "en": {
        "title": "OBD-II DIAGNOSTIC REPORT",
        "pdf_title": "OBD-II Diagnostic Report",
        "report_id": "Report ID",
        "created": "Created",
        "status": "Status",
        "model": "Model",
        "vin": "VIN",
        "not_specified": "Not specified",
        "not_available": "Not available",
        "report_text": "Report (text)",
        "report_unavailable": "Report not available.",
        "criteria": "Criteria",
    },
}


def _normalize_language(value: Optional[str]) -> str:
    if not value:
        return "es"
    lang = str(value).lower()
    if lang.startswith("en"):
        return "en"
    if lang.startswith("es"):
        return "es"
    return "es"


def render_report_pdf(
    payload: Dict[str, Any],
    output_path: Path,
    *,
    report_json: Optional[Dict[str, Any]] = None,
    report_text: Optional[str] = None,
    language: Optional[str] = None,
) -> Path:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            ListFlowable,
            ListItem,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise RuntimeError("Missing dependency: reportlab") from exc

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0B2E4E"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeader",
            parent=styles["Heading2"],
            fontSize=12,
            leading=14,
            textColor=colors.HexColor("#0B2E4E"),
            spaceBefore=8,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyTextCompact",
            parent=styles["BodyText"],
            fontSize=10,
            leading=13,
        )
    )

    def para(text: str, style_name: str = "BodyTextCompact") -> Paragraph:
        safe = escape(text).replace("\n", "<br/>")
        return Paragraph(safe, styles[style_name])

    if isinstance(report_json, dict) and not language:
        language = report_json.get("language")
    lang = _normalize_language(language)
    labels = META_LABELS[lang]
    section_titles = SECTION_TITLES[lang]
    section_order = list(zip(SECTION_KEYS, section_titles))

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title=labels["pdf_title"],
    )

    story: List[Any] = []

    story.append(para(labels["title"], "ReportTitle"))

    report_id = str(payload.get("report_id", ""))
    created_at = str(payload.get("created_at", ""))
    status = str(payload.get("status", ""))
    model = str(payload.get("model", ""))
    vehicle = payload.get("vehicle") or {}
    vin_value = ""
    if isinstance(vehicle, dict):
        vin_value = str(vehicle.get("vin") or "")
    meta_rows = [
        [labels["report_id"], report_id, labels["created"], created_at],
        [labels["status"], status, labels["model"], model],
        [labels["vin"], vin_value or labels["not_available"], "", ""],
    ]
    meta_table = Table(meta_rows, colWidths=[1.1 * inch, 2.2 * inch, 0.9 * inch, 2.2 * inch])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7EEF6")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F6F8FB")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C7DA")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D0DAE6")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 10))

    sections = {}
    if isinstance(report_json, dict):
        raw_sections = report_json.get("sections")
        if isinstance(raw_sections, dict):
            sections = raw_sections
        else:
            sections = report_json

    def render_list(items: Sequence[str], *, ordered: bool = False) -> ListFlowable:
        list_items = [ListItem(para(item)) for item in items]
        return ListFlowable(list_items, bulletType="1" if ordered else "bullet", start=1)

    if sections:
        for key, title in section_order:
            story.append(para(title, "SectionHeader"))
            value = sections.get(key)
            if value is None or value == "":
                fallback = labels["not_available"] if key == "4_evidencia_datos_en_vivo" else labels["not_specified"]
                story.append(para(fallback))
                continue

            if key == "6_causas_probables":
                items = []
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            prioridad = str(item.get("prioridad") or item.get("priority") or "").strip()
                            causa = str(item.get("causa") or item.get("cause") or "").strip()
                            label = f"{prioridad}: {causa}".strip(": ")
                            if label:
                                items.append(label)
                        elif isinstance(item, str):
                            items.append(item)
                if items:
                    story.append(render_list(items))
                else:
                    story.append(para(labels["not_specified"]))
                continue

            if key == "7_pruebas_recomendadas":
                items = []
                if isinstance(value, list):
                    for idx, item in enumerate(value, start=1):
                        if isinstance(item, dict):
                            descripcion = str(item.get("descripcion") or item.get("description") or "").strip()
                            criterio = str(
                                item.get("criterio_confirmacion") or item.get("confirmation_criteria") or ""
                            ).strip()
                            if criterio:
                                line = f"{descripcion} ({labels['criteria']}: {criterio})".strip()
                            else:
                                line = descripcion
                            if line:
                                items.append(line)
                        elif isinstance(item, str):
                            items.append(item)
                        else:
                            items.append(str(item))
                if items:
                    story.append(render_list(items, ordered=True))
                else:
                    story.append(para(labels["not_specified"]))
                continue

            if key == "8_acciones_recomendadas":
                items = []
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            causa = str(item.get("causa") or item.get("cause") or "").strip()
                            accion = str(item.get("accion") or item.get("action") or "").strip()
                            if causa and accion:
                                items.append(f"{causa}: {accion}")
                            elif accion:
                                items.append(accion)
                        elif isinstance(item, str):
                            items.append(item)
                if items:
                    story.append(render_list(items))
                else:
                    story.append(para(labels["not_specified"]))
                continue

            if isinstance(value, list):
                items = [str(item) for item in value if item]
                if items:
                    story.append(render_list(items))
                else:
                    story.append(para(labels["not_specified"]))
                continue

            story.append(para(str(value)))

    elif report_text:
        story.append(para(labels["report_text"], "SectionHeader"))
        story.append(para(report_text))
    else:
        story.append(para(labels["report_unavailable"]))

    doc.build(story)
    return output_path
