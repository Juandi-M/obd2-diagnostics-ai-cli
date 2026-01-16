"""
OBD-II Scanner Utilities
========================
Shared utilities, constants, and timezone handling.
"""

from datetime import datetime, timezone, timedelta

# Costa Rica timezone (UTC-6)
CR_TZ = timezone(timedelta(hours=-6))


def cr_now() -> datetime:
    """Get current time in Costa Rica timezone."""
    return datetime.now(CR_TZ)


def cr_timestamp() -> str:
    """Get formatted timestamp string."""
    return cr_now().strftime("%Y-%m-%d %H:%M:%S")


def cr_timestamp_filename() -> str:
    """Get timestamp suitable for filenames."""
    return cr_now().strftime("%Y-%m-%d_%H-%M-%S")


def cr_time_only() -> str:
    """Get time only (HH:MM:SS)."""
    return cr_now().strftime("%H:%M:%S")


# Version info
VERSION = "2.0.0"
APP_NAME = "OBD-II Scanner"
