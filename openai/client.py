from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict, List, Optional


class OpenAIError(Exception):
    pass


def get_api_key() -> Optional[str]:
    return os.environ.get("OPENAI_API_KEY")


def get_model() -> str:
    return os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def chat_completion(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    api_key = get_api_key()
    if not api_key:
        raise OpenAIError("Missing OPENAI_API_KEY")
    payload = {
        "model": get_model(),
        "messages": messages,
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            body = response.read().decode("utf-8")
    except Exception as exc:
        raise OpenAIError(str(exc)) from exc
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise OpenAIError("Invalid JSON response") from exc
    return data
