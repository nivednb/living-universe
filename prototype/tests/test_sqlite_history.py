"""Tests for the opt-in SQLite ledger; no kernel persistence migration yet."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlite_history import HistoryIntegrityError, SQLiteHistoryLedger


class SQLiteLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "history.sqlite"

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_roundtrip_and_reopen(self):
        records = [(0, 2, "discovery", 7, {"source": [2, 4], "name": "魔法"}),
                   (1, 2, "journey", None, {"x": [True, None, 0.25]})]
        with SQLiteHistoryLedger(self.path) as ledger:
            self.assertEqual(ledger.append_many(records), 2)
            self.assertEqual(list(ledger.iter_events(batch_size=1)), records)
        with SQLiteHistoryLedger(self.path) as ledger:
            self.assertEqual(ledger.cursor(), (1, 2))
            self.assertEqual(list(ledger.iter_events(actor=7)), records[:1])
            self.assertEqual(list(ledger.iter_events(start_day=3)), [])

    def test_reject_duplicate_and_out_of_order(self):
        with SQLiteHistoryLedger(self.path) as ledger:
            ledger.append_many([(0, 0, "start", None, {})])
            with self.assertRaises(HistoryIntegrityError):
                ledger.append_many([(0, 0, "start", None, {})])
            with self.assertRaises(ValueError):
                ledger.append_many([(2, 1, "a", None, {}), (1, 1, "b", None, {})])
            self.assertEqual(ledger.cursor(), (0, 1))

    def test_batch_rollback(self):
        with SQLiteHistoryLedger(self.path) as ledger:
            with self.assertRaises(sqlite3.IntegrityError):
                ledger.append_many([(1, 1, "a", None, {}), (1, 1, "b", None, {})])
            self.assertEqual(ledger.cursor(), (None, 0))

    def test_reject_invalid_and_corruption(self):
        with SQLiteHistoryLedger(self.path) as ledger:
            with self.assertRaises(ValueError):
                ledger.append_many([(0, 0, "a", None, {"bad": float("nan")})])
            with self.assertRaises(ValueError):
                ledger.append_many([(True, 0, "a", None, {})])
            ledger.append_many([(0, 0, "a", None, {"v": 1})])
            ledger.db.execute("UPDATE events SET payload=? WHERE sequence=0", ('{"v":2}',))
            ledger.db.commit()
            with self.assertRaises(HistoryIntegrityError):
                list(ledger.iter_events())


if __name__ == "__main__":
    unittest.main()
