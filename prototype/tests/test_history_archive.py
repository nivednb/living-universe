"""Roundtrip export bridge tests for the existing simulation history."""
import tempfile
import unittest
from pathlib import Path

from history_archive import export_history, verify_history
from archived_events import ArchivedEvents
from history import Event
from sqlite_history import HistoryIntegrityError, SQLiteHistoryLedger
from test_unified_persistence import make_world


class HistoryArchiveTests(unittest.TestCase):
    def test_negative_year_roundtrip(self):
        world = make_world()
        world.history.record(Event("ancient", -100, "Before epoch", frozenset({1})))
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "events.sqlite") as ledger:
                export_history(world, ledger)
                self.assertEqual(verify_history(world, ledger), len(world.history.events))
                self.assertEqual(ArchivedEvents(ledger)["ancient"].year, -100)

    def test_export_preserves_events_and_digest(self):
        world = make_world()
        world.research(1, "hybrid", 2)
        world.advance(2)
        original = world.digest()
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "events.sqlite") as ledger:
                self.assertEqual(export_history(world, ledger), len(world.history.events))
                self.assertEqual(verify_history(world, ledger), len(world.history.events))
                with self.assertRaises(HistoryIntegrityError):
                    export_history(world, ledger)
                ledger.db.execute("UPDATE events SET day = day + 1 WHERE sequence=0")
                ledger.db.commit()
                with self.assertRaises(HistoryIntegrityError):
                    verify_history(world, ledger)
        self.assertEqual(world.digest(), original)


if __name__ == "__main__":
    unittest.main()
