"""Reversible kernel event-mapping substitution tests."""
import tempfile
import unittest
from pathlib import Path

from archive_kernel_probe import probe_archived_kernel
from history_archive import export_history
from sqlite_history import HistoryIntegrityError, SQLiteHistoryLedger
from test_unified_persistence import make_world


class ArchivedKernelProbeTests(unittest.TestCase):
    def test_snapshot_and_validation_with_archived_mapping(self):
        world = make_world()
        world.research(1, "hybrid", 3)  # Populate history; empty fixtures cannot test corruption.
        original = world.history.events
        before = world.snapshot()
        with tempfile.TemporaryDirectory() as folder:
            with SQLiteHistoryLedger(Path(folder) / "history.sqlite") as ledger:
                export_history(world, ledger)
                result = probe_archived_kernel(world, ledger)
                self.assertEqual(result, before)
                self.assertIs(world.history.events, original)

    def test_mismatch_restores_original_mapping(self):
        world = make_world()
        world.research(1, "hybrid", 3)  # Populate history; empty fixtures cannot test corruption.
        original = world.history.events
        with tempfile.TemporaryDirectory() as folder:
            with SQLiteHistoryLedger(Path(folder) / "history.sqlite") as ledger:
                with self.assertRaises(HistoryIntegrityError):
                    probe_archived_kernel(world, ledger)
                self.assertIs(world.history.events, original)


if __name__ == "__main__":
    unittest.main()
