from __future__ import annotations

import re

from app.application.state import AppState
from app.application.vehicle import apply_brand_selection, get_brand_options, save_profile_for_group


class VehicleService:
    def __init__(self, state: AppState) -> None:
        self.state = state

    def get_brand_options(self):
        return get_brand_options()

    def apply_brand_selection(self, brand_id: str) -> bool:
        return apply_brand_selection(self.state, brand_id)

    def save_profile_for_group(self) -> None:
        save_profile_for_group(self.state)

    def apply_manual_profile(
        self,
        make_input: str,
        model_input: str,
        year_input: str,
        trim_input: str,
    ) -> tuple[dict[str, str | None], bool] | None:
        current = self.state.vehicle_profile or {}
        make = (make_input or "").strip()
        model = (model_input or "").strip()
        year = (year_input or "").strip()
        trim = (trim_input or "").strip()

        if not make and current.get("make"):
            make = str(current.get("make", ""))
        if not model and current.get("model"):
            model = str(current.get("model", ""))
        if not year and current.get("year"):
            year = str(current.get("year", ""))
        if not trim and current.get("trim"):
            trim = str(current.get("trim", ""))

        parsed = False
        if make and not any([model, year, trim]):
            match = re.search(r"\\b(19|20)\\d{2}\\b", make)
            if match:
                parsed = True
                parsed_year = match.group(0)
                before = make[: match.start()].strip(" ,-_")
                after = make[match.end() :].strip(" ,-_")
                parsed_make = before
                parsed_model = ""
                if before.lower().startswith("land rover "):
                    parsed_make = "Land Rover"
                    parsed_model = before[len("land rover ") :].strip()
                if parsed_model:
                    model = parsed_model
                if parsed_make:
                    make = parsed_make
                year = year or parsed_year
                if after and not trim:
                    trim = after

        if not any([make, model, year, trim]):
            return None

        profile = {
            "make": make or None,
            "model": model or None,
            "year": year or None,
            "trim": trim or None,
            "source": "manual",
        }
        self.state.vehicle_profile = profile
        return profile, parsed
