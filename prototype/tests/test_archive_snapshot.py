"""Archive snapshot equivalence and tamper rejection."""
import tempfile
import unittest
from pathlib import Path

from archive_snapshot import snapshot_with_archive
from history_archive import export_history
from sqlite_history import HistoryIntegrityError, SQLiteHistoryLedger
from test_unified_persistence import make_world
from unified_persistence import decode


class ArchiveSnapshotTests(unittest.TestCase):
    def test_snapshot_equivalence_and_restore(self):
        world = make_world()
        world.research(1, "hybrid", 2)
        world.advance(2)
        before = world.snapshot()
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                export_history(world, ledger)
                mirrored = snapshot_with_archive(world, ledger)
                self.assertEqual(mirrored, before)
                self.assertEqual(decode(mirrored).snapshot(), before)
                ledger.db.execute("UPDATE events SET payload=? WHERE sequence=0", ('{}',))
                ledger.db.commit()
                with self.assertRaises(HistoryIntegrityError):
                    snapshot_with_archive(world, ledger)


if __name__ == "__main__":
    unittest.main()
