from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


class OpenAIError(Exception):
    pass


def get_api_key() -> Optional[str]:
    return os.environ.get("OPENAI_API_KEY")


def get_model() -> str:
    return os.environ.get("OPENAI_MODEL", "gpt-5.2-thinking")


def chat_completion(
    messages: List[Dict[str, str]],
    *,
    temperature: float = 0.2,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    api_key = get_api_key()
    if not api_key:
        raise OpenAIError("Missing OPENAI_API_KEY")
    payload: Dict[str, Any] = {
        "model": model or get_model(),
        "messages": messages,
        "temperature": temperature,
    }
    if top_p is not None:
        payload["top_p"] = top_p
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
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
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            pass
        detail = body or str(exc)
        try:
            data = json.loads(body) if body else {}
            message = data.get("error", {}).get("message")
            if message:
                detail = message
        except Exception:
            pass
        raise OpenAIError(f"HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise OpenAIError(str(exc)) from exc
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise OpenAIError("Invalid JSON response") from exc
    return data
