from __future__ import annotations

from typing import List, Optional


def short_id(value: Optional[str]) -> str:
    if not value:
        return "-"
    if len(value) <= 8:
        return value
    return f"{value[:4]}...{value[-4:]}"


def header_lines(title: str) -> List[str]:
    return ["", "=" * 60, f"  {title}", "=" * 60]


def subheader_lines(title: str) -> List[str]:
    return ["", "-" * 40, f"  {title}", "-" * 40]

