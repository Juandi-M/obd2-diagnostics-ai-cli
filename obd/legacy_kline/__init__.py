"""
Legacy K-Line support (ISO9141 / KWP2000) via ELM327.

Stage 2.5: detection + apply + verify + basic routing.
"""

from .profiles.base import KLineProfile

from .runtime.policy import KLinePolicy
from .config.apply import apply_profile
from .config.verify import verify_profile
from .config.detect import detect_profile, detect_profile_report
from .session import LegacyKLineSession
from .scanner import LegacyKLineScanner

__all__ = [
    "KLineProfile",
    "KLinePolicy",
    "apply_profile",
    "verify_profile",
    "detect_profile",
    "detect_profile_report",
    "LegacyKLineSession",
    "LegacyKLineScanner",
]
