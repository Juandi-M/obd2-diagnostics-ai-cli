from __future__ import annotations

from app.i18n import t
from app.state import AppState
from app.ui import print_header


def run_ai_report(state: AppState) -> None:
    del state
    print_header(t("ai_report_header"))
    print(f"\n  🧠 {t('ai_report_stub')}")
