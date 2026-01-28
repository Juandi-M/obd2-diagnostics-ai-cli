"""
Legacy K-Line support (ISO9141 / KWP2000) via ELM327.

Stage 2.5: detection + apply + verify + basic routing.
"""

from .profiles.base import KLineProfile
from .runtime.policy import KLinePolicy
from .config.detect import detect_profile
from .config.apply import apply_profile
from .config.verify import verify_profile

__all__ = [
    "KLineProfile",
    "KLinePolicy",
    "detect_profile",
    "apply_profile",
    "verify_profile",
]
