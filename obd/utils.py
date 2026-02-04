"""
OBD-II Scanner Utilities (compat shim).
"""

from app.application.time_utils import (
    APP_NAME,
    CR_TZ,
    VERSION,
    cr_now,
    cr_time_only,
    cr_timestamp,
    cr_timestamp_filename,
)

__all__ = [
    "CR_TZ",
    "VERSION",
    "APP_NAME",
    "cr_now",
    "cr_timestamp",
    "cr_timestamp_filename",
    "cr_time_only",
]
