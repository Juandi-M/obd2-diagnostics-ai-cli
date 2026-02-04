from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain.ports import VinCacheRepository


class VinCacheService:
    def __init__(self, repo: VinCacheRepository) -> None:
        self.repo = repo

    def get(self, vin: str) -> Optional[Dict[str, Any]]:
        return self.repo.get(vin)

    def set(self, vin: str, profile: Dict[str, Any]) -> None:
        self.repo.set(vin, profile)
