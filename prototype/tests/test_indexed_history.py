"""Indexed historical event lookup and migration regressions."""
import tempfile
import unittest
from pathlib import Path

from sqlite_history import SQLiteHistoryLedger, HistoryIntegrityError


class IndexedHistoryTests(unittest.TestCase):
    def test_indexed_lookup_and_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.sqlite"
            with SQLiteHistoryLedger(path) as ledger:
                ledger.append_many((i, i, "historical_event", None,
                                    {"id": f"e-{i}", "description": str(i), "witnesses": []})
                                   for i in range(100))
                self.assertEqual(ledger.get_event_by_id("e-70")[0], 70)
                self.assertIsNone(ledger.get_event_by_id("missing"))
                with self.assertRaises(Exception):
                    ledger.append_many([(100, 100, "historical_event", None,
                                         {"id": "e-70", "description": "duplicate", "witnesses": []})])
                self.assertEqual(ledger.cursor(), (99, 100))
            with SQLiteHistoryLedger(path) as ledger:
                self.assertEqual(ledger.get_event_by_id("e-70")[4]["id"], "e-70")

    def test_explicit_legacy_index_rebuild(self):
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                ledger.append_many([(0, 0, "historical_event", None,
                                     {"id": "old", "description": "old", "witnesses": []})])
                ledger.db.execute("DELETE FROM event_ids")
                ledger.db.commit()
                with self.assertRaises(HistoryIntegrityError):
                    ledger.get_event_by_id("old")
                self.assertEqual(ledger.rebuild_event_id_index(), 1)
                self.assertEqual(ledger.get_event_by_id("old")[0], 0)


if __name__ == "__main__":
    unittest.main()
