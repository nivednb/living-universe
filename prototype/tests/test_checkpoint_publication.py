"""Checkpoint publication crash boundary tests."""
import tempfile
import unittest
from pathlib import Path

from checkpoint_publication import publish_checkpoint, recover_checkpoint
from history_archive import export_history
from sqlite_history import HistoryIntegrityError, SQLiteHistoryLedger
from test_unified_persistence import make_world


class PublicationTests(unittest.TestCase):
    def test_publish_and_recover(self):
        world = make_world()
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / "world.json"
            with SQLiteHistoryLedger(Path(folder) / "events.sqlite") as ledger:
                export_history(world, ledger)
                digest = publish_checkpoint(world, ledger, checkpoint)
                self.assertEqual(len(digest), 64)
                self.assertEqual(recover_checkpoint(ledger, checkpoint).snapshot(), world.snapshot())

    def test_recover_interrupted_rename(self):
        world = make_world()
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / "world.json"
            with SQLiteHistoryLedger(Path(folder) / "events.sqlite") as ledger:
                export_history(world, ledger)
                publish_checkpoint(world, ledger, checkpoint)
                candidate = checkpoint.with_name(checkpoint.name + ".pending")
                checkpoint.replace(candidate)
                ledger.db.execute("UPDATE checkpoint_publication SET status='prepared' WHERE id=1")
                ledger.db.commit()
                self.assertEqual(recover_checkpoint(ledger, checkpoint).snapshot(), world.snapshot())
                self.assertTrue(checkpoint.exists())

    def test_reject_tampered_candidate(self):
        world = make_world()
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / "world.json"
            with SQLiteHistoryLedger(Path(folder) / "events.sqlite") as ledger:
                export_history(world, ledger)
                publish_checkpoint(world, ledger, checkpoint)
                candidate = checkpoint.with_name(checkpoint.name + ".pending")
                checkpoint.replace(candidate)
                candidate.write_text("{}", encoding="utf-8")
                ledger.db.execute("UPDATE checkpoint_publication SET status='prepared' WHERE id=1")
                ledger.db.commit()
                with self.assertRaises(HistoryIntegrityError):
                    recover_checkpoint(ledger, checkpoint)


if __name__ == "__main__":
    unittest.main()
