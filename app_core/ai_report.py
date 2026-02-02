from __future__ import annotations

import json
from typing import Any, Dict, Optional

from openai.client import chat_completion
from openai.client import OpenAIError


def decode_vin_with_ai(vin: str, manufacturer: str) -> Optional[Dict[str, Any]]:
    system_lines = [
        "You decode VINs into vehicle specs.",
        "Return ONLY valid JSON. No extra text.",
        "If unsure, leave fields empty.",
    ]
    user_lines = [
        f"VIN: {vin}",
        f"Brand selection: {manufacturer}",
        "Return JSON with this schema:",
        "{",
        '  "make": "",',
        '  "model": "",',
        '  "year": "",',
        '  "trim": "",',
        '  "engine": "",',
        '  "confidence": "high|medium|low",',
        '  "notes": ""',
        "}",
    ]
    messages = [
        {"role": "system", "content": "\n".join(system_lines)},
        {"role": "user", "content": "\n".join(user_lines)},
    ]
    response = chat_completion(
        messages,
        temperature=0.0,
        top_p=1.0,
        max_tokens=220,
        model="gpt-4o-mini",
    )
    choices = response.get("choices", [])
    if not choices:
        return None
    content = choices[0].get("message", {}).get("content", "")
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                return None
        return None


def request_ai_report(report_input: Dict[str, Any], language: str) -> str:
    lang = "es" if str(language).lower().startswith("es") else "en"
    if lang == "es":
        system_lines = [
            "Eres un sistema de diagnóstico automotriz profesional.",
            "Escribes reportes técnicos estandarizados para talleres mecánicos.",
            "No uses emojis, jerga, ni menciones IA/ChatGPT.",
            "Mantén un tono formal, directo, y orientado a pruebas.",
            "Si falta evidencia, decláralo en 'Notas y limitaciones' y sugiere cómo confirmarlo.",
        ]
        user_lines = [
            "Genera un reporte en ESPAÑOL con la siguiente estructura fija:",
            "1) Identificación del vehículo",
            "2) Motivo de visita / Síntomas reportados",
            "3) Resultado del escaneo (DTCs, MIL, readiness)",
            "4) Evidencia en datos en vivo (si existe; si no, indicar 'No disponible')",
            "5) Interpretación técnica (basada en evidencia)",
            "6) Causas probables (priorizadas con Alta/Media/Baja)",
            "7) Pruebas recomendadas (pasos enumerados; incluir criterio de confirmación)",
            "8) Acciones recomendadas (solo si se confirma cada causa)",
            "9) Notas y limitaciones",
            "10) Timestamp",
            "",
            "Reglas:",
            "- No inventar datos. Si un dato no viene, indicar 'No especificado'.",
            "- No recomendar reemplazos hasta proponer pruebas de confirmación.",
            "- Máximo 1 página (aprox. 350-500 palabras).",
            "- Usar lenguaje técnico de taller.",
        ]
    else:
        system_lines = [
            "You are a professional automotive diagnostic system.",
            "You write standardized technical reports for auto repair shops.",
            "Do not use emojis, slang, or mention AI/ChatGPT.",
            "Keep a formal, direct, test-oriented tone.",
            "If evidence is missing, state it in 'Notes and limitations' and suggest how to confirm it.",
        ]
        user_lines = [
            "Generate a report in ENGLISH with the following fixed structure:",
            "1) Vehicle identification",
            "2) Reason for visit / reported symptoms",
            "3) Scan results (DTCs, MIL, readiness)",
            "4) Live data evidence (if available; otherwise say 'Not available')",
            "5) Technical interpretation (based on evidence)",
            "6) Probable causes (prioritized with High/Medium/Low)",
            "7) Recommended tests (numbered steps; include confirmation criteria)",
            "8) Recommended actions (only if each cause is confirmed)",
            "9) Notes and limitations",
            "10) Timestamp",
            "",
            "Rules:",
            "- Do not invent data. If a value is missing, write 'Not specified'.",
            "- Do not recommend part replacement until you propose confirmation tests.",
            "- Max 1 page (approx. 350-500 words).",
            "- Use shop-technical language.",
        ]

    output_lines = [
        "",
        "Salida requerida (obligatoria):" if lang == "es" else "Required output (mandatory):",
        "- Devuelve primero un objeto JSON válido." if lang == "es" else "- Return a valid JSON object first.",
        "- Encierra el JSON entre <json> y </json>." if lang == "es" else "- Wrap the JSON between <json> and </json>.",
        "- Luego, en una nueva línea, entrega el reporte en texto plano."
        if lang == "es"
        else "- Then, on a new line, provide the report in plain text.",
        "- Encierra el texto entre <report> y </report>."
        if lang == "es"
        else "- Wrap the text between <report> and </report>.",
        "- No agregues contenido fuera de esas etiquetas."
        if lang == "es"
        else "- Do not add content outside those tags.",
        "",
        "El JSON debe usar este esquema exacto (nombres de campos fijos):"
        if lang == "es"
        else "The JSON must use this exact schema (field names are fixed):",
        "{",
        f'  "language": "{lang}",',
        '  "sections": {',
        '    "1_identificacion_vehiculo": "...",',
        '    "2_motivo_visita": "...",',
        '    "3_resultado_escaneo": "...",',
        '    "4_evidencia_datos_en_vivo": "...",',
        '    "5_interpretacion_tecnica": "...",',
        '    "6_causas_probables": [',
        '      {"prioridad": "Alta|Media|Baja", "causa": "..."}',
        "    ],",
        '    "7_pruebas_recomendadas": [',
        '      {"paso": 1, "descripcion": "...", "criterio_confirmacion": "..."}',
        "    ],",
        '    "8_acciones_recomendadas": [',
        '      {"causa": "...", "accion": "..."}',
        "    ],",
        '    "9_notas_limitaciones": "...",',
        '    "10_timestamp": "..."',
        "  }",
        "}",
        "",
        "Datos de entrada:" if lang == "es" else "Input data:",
        json.dumps(report_input, ensure_ascii=False, indent=2),
    ]
    user_lines = user_lines + output_lines
    messages = [
        {
            "role": "system",
            "content": "\n".join(system_lines),
        },
        {
            "role": "user",
            "content": "\n".join(user_lines),
        },
    ]
    response = chat_completion(messages, temperature=0.2, top_p=0.9, max_tokens=900)
    choices = response.get("choices", [])
    if not choices:
        raise OpenAIError("No response choices returned.")
    message = choices[0].get("message", {})
    content = message.get("content")
    if not content:
        raise OpenAIError("Empty response content.")
    return content
