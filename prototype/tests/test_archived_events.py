"""Archive read-through avoids materializing an event dictionary."""
import tempfile
import unittest
from pathlib import Path
from archived_events import ArchivedEvents
from history_archive import export_history
from sqlite_history import SQLiteHistoryLedger
from test_unified_persistence import make_world


class ArchivedEventsTests(unittest.TestCase):
    def test_read_through_and_missing(self):
        world = make_world()
        world.research(1, "hybrid", 2)
        world.advance(2)
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "events.sqlite") as ledger:
                export_history(world, ledger)
                archived = ArchivedEvents(ledger)
                self.assertEqual(len(archived), len(world.history.events))
                self.assertEqual(list(archived), list(world.history.events))
                for key, event in world.history.events.items():
                    self.assertEqual(archived[key], event)
                with self.assertRaises(KeyError):
                    archived["missing"]


if __name__ == "__main__":
    unittest.main()
