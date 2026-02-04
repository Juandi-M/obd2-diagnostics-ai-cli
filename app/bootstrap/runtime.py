from __future__ import annotations

from app.infrastructure.persistence.env import load_dotenv


def init_environment() -> None:
    load_dotenv()
