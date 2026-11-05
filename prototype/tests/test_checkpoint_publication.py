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
        world.research(1, "hybrid", 3)  # Populate history; empty fixtures cannot test corruption.
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / "world.json"
            with SQLiteHistoryLedger(Path(folder) / "events.sqlite") as ledger:
                export_history(world, ledger)
                digest = publish_checkpoint(world, ledger, checkpoint)
                self.assertEqual(len(digest), 64)
                self.assertEqual(recover_checkpoint(ledger, checkpoint).snapshot(), world.snapshot())

    def test_recovery_after_rename_before_final_status(self):
        world = make_world()
        world.research(1, "hybrid", 3)  # Populate history; empty fixtures cannot test corruption.
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / "world.json"
            with SQLiteHistoryLedger(Path(folder) / "events.sqlite") as ledger:
                export_history(world, ledger)
                publish_checkpoint(world, ledger, checkpoint)
                ledger.db.execute(
                    "UPDATE checkpoint_publication SET status='prepared' WHERE id=1"
                )
                ledger.db.commit()
                restored = recover_checkpoint(ledger, checkpoint)
                self.assertEqual(restored.snapshot(), world.snapshot())
                self.assertEqual(ledger.db.execute(
                    "SELECT status FROM checkpoint_publication WHERE id=1"
                ).fetchone()[0], "published")

    def test_recover_interrupted_rename(self):
        world = make_world()
        world.research(1, "hybrid", 3)  # Populate history; empty fixtures cannot test corruption.
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

    def test_recovery_does_not_publish_unverified_archive(self):
        world = make_world()
        world.research(1, "hybrid", 3)  # Populate history; empty fixtures cannot test corruption.
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / "world.json"
            with SQLiteHistoryLedger(Path(folder) / "events.sqlite") as ledger:
                export_history(world, ledger)
                publish_checkpoint(world, ledger, checkpoint)
                ledger.db.execute(
                    "UPDATE checkpoint_publication SET status='prepared' WHERE id=1"
                )
                ledger.db.execute("UPDATE events SET payload='{}' WHERE sequence=0")
                ledger.db.commit()
                with self.assertRaises(HistoryIntegrityError):
                    recover_checkpoint(ledger, checkpoint)
                status = ledger.db.execute(
                    "SELECT status FROM checkpoint_publication WHERE id=1"
                ).fetchone()[0]
                self.assertEqual(status, "prepared")

    def test_recovery_replaces_older_checkpoint_from_prepared_candidate(self):
        world = make_world()
        world.research(1, "hybrid", 3)  # Populate history; empty fixtures cannot test corruption.
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / "world.json"
            with SQLiteHistoryLedger(Path(folder) / "events.sqlite") as ledger:
                export_history(world, ledger)
                publish_checkpoint(world, ledger, checkpoint)
                # Simulate crash after the next publication intent was
                # committed, while the old public checkpoint still exists.
                candidate = checkpoint.with_name(checkpoint.name + ".pending")
                checkpoint.replace(candidate)
                checkpoint.write_bytes(b"older checkpoint bytes")
                ledger.db.execute(
                    "UPDATE checkpoint_publication SET status='prepared' WHERE id=1"
                )
                ledger.db.commit()
                self.assertEqual(recover_checkpoint(ledger, checkpoint).snapshot(), world.snapshot())
                self.assertFalse(candidate.exists())

    def test_unrecorded_candidate_blocks_publication(self):
        world = make_world()
        world.research(1, "hybrid", 3)  # Populate history; empty fixtures cannot test corruption.
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / "world.json"
            candidate = checkpoint.with_name(checkpoint.name + ".pending")
            candidate.write_bytes(b"interrupted before SQLite intent")
            with SQLiteHistoryLedger(Path(folder) / "events.sqlite") as ledger:
                export_history(world, ledger)
                with self.assertRaises(HistoryIntegrityError):
                    publish_checkpoint(world, ledger, checkpoint)
                self.assertEqual(candidate.read_bytes(), b"interrupted before SQLite intent")
                self.assertFalse(checkpoint.exists())

    def test_reject_tampered_candidate(self):
        world = make_world()
        world.research(1, "hybrid", 3)  # Populate history; empty fixtures cannot test corruption.
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
