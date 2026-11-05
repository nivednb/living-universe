"""Recovery gate rejects stale or corrupted cross-store states."""
import tempfile
import unittest
from pathlib import Path

from archive_recovery import check_checkpoint_cursor, load_verified_checkpoint
from history_archive import export_history
from sqlite_history import HistoryIntegrityError, SQLiteHistoryLedger
from test_unified_persistence import make_world
from unified_persistence import save


class ArchiveRecoveryTests(unittest.TestCase):
    def test_matching_checkpoint_and_archive(self):
        world = make_world()
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "world.json"
            save(world, checkpoint)
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                export_history(world, ledger)
                self.assertEqual(load_verified_checkpoint(checkpoint, ledger).snapshot(), world.snapshot())
                self.assertEqual(check_checkpoint_cursor(checkpoint, ledger)[1], len(world.history.events))

    def test_archive_ahead_of_checkpoint_rejected(self):
        world = make_world()
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "world.json"
            save(world, checkpoint)
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                export_history(world, ledger)
                last, count = ledger.cursor()
                ledger.append_many([(count, world.day, "historical_event", None,
                                     {"id": "orphan", "year": world.day,
                                      "description": "uncheckpointed", "witnesses": []})])
                with self.assertRaises(HistoryIntegrityError):
                    load_verified_checkpoint(checkpoint, ledger)

    def test_archive_behind_checkpoint_rejected(self):
        world = make_world()
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "world.json"
            save(world, checkpoint)
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                with self.assertRaises(HistoryIntegrityError):
                    load_verified_checkpoint(checkpoint, ledger)


if __name__ == "__main__":
    unittest.main()
