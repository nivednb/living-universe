"""Atomic event/witness storage regression tests."""
import tempfile
import unittest
from pathlib import Path

from atomic_witness_archive import append_event_with_witnesses, verify_witness_memory
from history import Event
from sqlite_history import HistoryIntegrityError, SQLiteHistoryLedger


class AtomicWitnessArchiveTests(unittest.TestCase):
    def test_witness_rows_survive_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.sqlite"
            with SQLiteHistoryLedger(path) as ledger:
                append_event_with_witnesses(ledger, Event("z", 0, "First", frozenset({3, 7})))
                append_event_with_witnesses(ledger, Event("a", 1, "Second", frozenset({7})))
                self.assertEqual(verify_witness_memory(ledger), 3)
            with SQLiteHistoryLedger(path) as ledger:
                self.assertEqual(verify_witness_memory(ledger), 3)
                self.assertEqual(ledger.cursor(), (1, 2))

    def test_duplicate_event_rolls_back_witnesses(self):
        with tempfile.TemporaryDirectory() as folder:
            with SQLiteHistoryLedger(Path(folder) / "history.sqlite") as ledger:
                append_event_with_witnesses(ledger, Event("same", 0, "First", frozenset({1})))
                with self.assertRaises(Exception):
                    append_event_with_witnesses(ledger, Event("same", 1, "Second", frozenset({2})))
                self.assertEqual(ledger.cursor(), (0, 1))
                self.assertEqual(verify_witness_memory(ledger), 1)

    def test_witness_insert_failure_rolls_back_event_and_index(self):
        with tempfile.TemporaryDirectory() as folder:
            with SQLiteHistoryLedger(Path(folder) / "history.sqlite") as ledger:
                record = (0, 0, "historical_event", None,
                          {"id": "rollback", "year": 0,
                           "description": "Test", "witnesses": [1]})
                with self.assertRaises(Exception):
                    ledger.append_many([record], witness_rows=[
                        ("rollback", 1), ("rollback", 1)
                    ])
                self.assertEqual(ledger.cursor(), (None, 0))
                self.assertIsNone(ledger.get_event_by_id("rollback"))
                self.assertEqual(ledger.db.execute(
                    "SELECT COUNT(*) FROM event_witness_memory"
                ).fetchone()[0], 0)

    def test_empty_archive_without_witness_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            with SQLiteHistoryLedger(Path(folder) / "history.sqlite") as ledger:
                self.assertEqual(verify_witness_memory(ledger), 0)

    def test_nonempty_archive_without_witness_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            with SQLiteHistoryLedger(Path(folder) / "history.sqlite") as ledger:
                ledger.append_many([(0, 0, "historical_event", None,
                                     {"id": "old", "year": 0,
                                      "description": "Legacy", "witnesses": [1]})])
                with self.assertRaises(HistoryIntegrityError):
                    verify_witness_memory(ledger)

    def test_missing_witness_row_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            with SQLiteHistoryLedger(Path(folder) / "history.sqlite") as ledger:
                append_event_with_witnesses(ledger, Event("event", 0, "First", frozenset({1})))
                with ledger.db:
                    ledger.db.execute("DELETE FROM event_witness_memory")
                with self.assertRaises(HistoryIntegrityError):
                    verify_witness_memory(ledger)


if __name__ == "__main__":
    unittest.main()
