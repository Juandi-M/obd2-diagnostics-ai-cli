from __future__ import annotations

from typing import Optional

from app.domain.ports import AiConfigPort


class AiConfigService:
    def __init__(self, config_port: AiConfigPort) -> None:
        self.config_port = config_port

    def get_api_key(self) -> Optional[str]:
        return self.config_port.get_api_key()

    def get_model(self) -> str:
        return self.config_port.get_model()

    def is_configured(self) -> bool:
        return bool(self.get_api_key())
