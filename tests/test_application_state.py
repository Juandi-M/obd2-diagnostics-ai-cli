from __future__ import annotations

import unittest

from app.application.state import AppState
from tests.app_fakes import DummyDtcDb, DummyDtcFactory, DummyKLineScanner, DummyScanner, DummyScannerFactory


class DummyRawLoggerFactory:
    def __init__(self) -> None:
        self.last_enabled = None

    def create(self, enabled: bool):
        self.last_enabled = enabled
        return "LOGGER" if enabled else None


class AppStateTests(unittest.TestCase):
    def test_ensure_scanner_uses_factory(self) -> None:
        factory = DummyScannerFactory()
        state = AppState(scanner_factory=factory)
        scanner = state.ensure_scanner()
        self.assertIsNotNone(scanner)
        self.assertEqual(factory.created, 1)

    def test_set_manufacturer_propagates(self) -> None:
        state = AppState()
        dtc_db = DummyDtcDb()
        scanner = DummyScanner()
        kline = DummyKLineScanner()
        state.dtc_db = dtc_db
        state.scanner = scanner
        state.kline_scanner = kline

        state.set_manufacturer("chrysler")

        self.assertEqual(dtc_db.manufacturer, "chrysler")
        self.assertEqual(scanner.manufacturer, "chrysler")
        self.assertEqual(kline.manufacturer, "chrysler")

    def test_active_scanner_prefers_kline(self) -> None:
        state = AppState()
        scanner = DummyScanner()
        kline = DummyKLineScanner()
        scanner.is_connected = True
        kline.is_connected = True
        state.scanner = scanner
        state.kline_scanner = kline

        active = state.active_scanner()
        self.assertIs(active, kline)

        kline.is_connected = False
        active = state.active_scanner()
        self.assertIs(active, scanner)

    def test_clear_kline_disconnects(self) -> None:
        state = AppState()
        kline = DummyKLineScanner()
        kline.is_connected = True
        state.kline_scanner = kline
        state.clear_kline_scanner()
        self.assertIsNone(state.kline_scanner)

    def test_disconnect_all(self) -> None:
        state = AppState()
        scanner = DummyScanner()
        scanner.is_connected = True
        kline = DummyKLineScanner()
        kline.is_connected = True
        state.scanner = scanner
        state.kline_scanner = kline
        state.disconnect_all()
        self.assertFalse(scanner.is_connected)
        self.assertIsNone(state.kline_scanner)

    def test_ensure_dtc_db(self) -> None:
        factory = DummyDtcFactory()
        state = AppState(dtc_db_factory=factory)
        db = state.ensure_dtc_db()
        self.assertIsNotNone(db)
        self.assertEqual(factory.created, 1)

    def test_set_verbose_updates_logger(self) -> None:
        logger_factory = DummyRawLoggerFactory()
        state = AppState(raw_logger_factory=logger_factory)
        scanner = DummyScanner()
        kline = DummyKLineScanner()
        state.scanner = scanner
        state.kline_scanner = kline

        state.set_verbose(True)
        self.assertEqual(scanner.raw_logger, "LOGGER")
        self.assertEqual(kline.raw_logger, "LOGGER")
