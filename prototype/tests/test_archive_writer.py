"""Direct historical event writer regressions."""
import tempfile
import unittest
from pathlib import Path

from archive_writer import ArchivedEventWriter
from history import Event
from sqlite_history import SQLiteHistoryLedger


class ArchiveWriterTests(unittest.TestCase):
    def test_deterministic_ids_and_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.sqlite"
            with SQLiteHistoryLedger(path) as ledger:
                writer = ArchivedEventWriter(ledger)
                first = writer.record_kernel(0, "arrival", 7, "Village", (7,))
                second = writer.record_kernel(1, "research", 7, "Pottery", (7,))
                self.assertEqual((first.id, second.id), ("kernel-0", "kernel-1"))
                self.assertEqual(writer.events["kernel-1"].description, "research: Pottery")
                self.assertEqual(ledger.cursor(), (1, 2))
            with SQLiteHistoryLedger(path) as ledger:
                writer = ArchivedEventWriter(ledger)
                self.assertEqual(writer.record_kernel(2, "teaching", 7, "Pottery", (7, 8)).id,
                                 "kernel-2")

    def test_duplicate_id_does_not_append(self):
        with tempfile.TemporaryDirectory() as folder:
            with SQLiteHistoryLedger(Path(folder) / "history.sqlite") as ledger:
                writer = ArchivedEventWriter(ledger)
                writer.record(Event("same", 0, "First", frozenset({1})))
                with self.assertRaises(Exception):
                    writer.record(Event("same", 1, "Duplicate", frozenset({1})))
                self.assertEqual(ledger.cursor(), (0, 1))

    def test_reserved_claim_collision(self):
        with tempfile.TemporaryDirectory() as folder:
            with SQLiteHistoryLedger(Path(folder) / "history.sqlite") as ledger:
                writer = ArchivedEventWriter(ledger, reserved_claim_ids={"kernel-0"})
                with self.assertRaises(ValueError):
                    writer.record_kernel(0, "arrival", 7, "Village", (7,))
                self.assertEqual(ledger.cursor(), (None, 0))

    def test_invalid_witness_does_not_write(self):
        with tempfile.TemporaryDirectory() as folder:
            with SQLiteHistoryLedger(Path(folder) / "history.sqlite") as ledger:
                writer = ArchivedEventWriter(ledger)
                with self.assertRaises(ValueError):
                    writer.record_kernel(0, "arrival", 7, "Village", (-1,))
                self.assertEqual(ledger.cursor(), (None, 0))

    def test_reject_negative_live_day(self):
        with tempfile.TemporaryDirectory() as folder:
            with SQLiteHistoryLedger(Path(folder) / "history.sqlite") as ledger:
                writer = ArchivedEventWriter(ledger)
                with self.assertRaises(ValueError):
                    writer.record(Event("ancient", -1, "Before epoch"))


if __name__ == "__main__":
    unittest.main()
