"""Epistemic archive validation regression tests."""
import tempfile
import unittest
from pathlib import Path

from archive_invariants import validate_archive_knowledge
from history_archive import export_history
from sqlite_history import HistoryIntegrityError, SQLiteHistoryLedger
from test_unified_persistence import make_world


class ArchiveInvariantTests(unittest.TestCase):
    def test_valid_world_archive(self):
        world = make_world()
        with tempfile.TemporaryDirectory() as folder:
            with SQLiteHistoryLedger(Path(folder) / "history.sqlite") as ledger:
                export_history(world, ledger)
                self.assertEqual(
                    validate_archive_knowledge(world, ledger),
                    len(world.history.events),
                )

    def test_unwitnessed_direct_memory_rejected(self):
        world = make_world()
        if not world.history.events or not world.travelers:
            self.skipTest("fixture has no historical events or travelers")
        event = next(iter(world.history.events.values()))
        nonwitness = next((actor for actor in world.travelers
                           if actor not in event.witnesses), None)
        if nonwitness is None:
            self.skipTest("fixture has no nonwitness actor")
        world.history.knowledge.setdefault(nonwitness, set()).add(event.id)
        with tempfile.TemporaryDirectory() as folder:
            with SQLiteHistoryLedger(Path(folder) / "history.sqlite") as ledger:
                export_history(world, ledger)
                with self.assertRaises(HistoryIntegrityError):
                    validate_archive_knowledge(world, ledger)

    def test_missing_archive_event_rejected(self):
        world = make_world()
        if not world.history.events:
            self.skipTest("fixture has no historical events")
        with tempfile.TemporaryDirectory() as folder:
            with SQLiteHistoryLedger(Path(folder) / "history.sqlite") as ledger:
                with self.assertRaises(HistoryIntegrityError):
                    validate_archive_knowledge(world, ledger)


if __name__ == "__main__":
    unittest.main()
