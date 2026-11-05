"""Optional PR3/PR4 compatibility tests; active when both modules are present.

Standalone PR4 deliberately does not depend on the unmerged archive branch.
The temporary combined audit checkout runs these tests without skips.
"""
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from history import Claim, Event
from test_unified_persistence import make_world
from views import character_view, observer_view, to_wire
from world_state import KnowledgeClaim

ARCHIVE_AVAILABLE = all(importlib.util.find_spec(name) is not None
                        for name in ("history_archive", "archived_events", "checkpoint_publication"))


@contextmanager
def archived_mapping(world, ledger):
    from archived_events import ArchivedEvents
    original = world.history.events
    try:
        world.history.events = ArchivedEvents(ledger)
        yield
    finally:
        world.history.events = original


def world_with_knowledge():
    world = make_world()
    world.history.record(Event("ancient", -100, "private historical truth", frozenset({1})))
    world.history.publish_claim(Claim("rumor", "ancient", "A disputed story", "archive"))
    world.history.communicate("rumor", 2)
    world.state.add_claim(KnowledgeClaim("belief", "Possibly true", "ancient", ("rumor",)))
    world.state.learn(2, "belief")
    world.depart(1, "market")
    world.research(1, "hybrid", 5)
    world.advance(2)
    world.validate()
    return world


@unittest.skipUnless(ARCHIVE_AVAILABLE, "requires the unmerged PR3 SQLite archive modules")
class ViewArchiveIntegrationTests(unittest.TestCase):
    def test_archive_backed_views_match_memory_views_without_mutating_stores(self):
        from history_archive import export_history
        from sqlite_history import SQLiteHistoryLedger
        world = world_with_knowledge()
        expected_observer = to_wire(observer_view(world))
        expected_characters = [to_wire(character_view(world, actor)) for actor in (1, 2)]
        before = world.digest()
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                export_history(world, ledger)
                database_before = tuple(ledger.db.iterdump())
                with archived_mapping(world, ledger):
                    self.assertEqual(to_wire(observer_view(world)), expected_observer)
                    self.assertEqual([to_wire(character_view(world, a)) for a in (1, 2)], expected_characters)
                self.assertEqual(tuple(ledger.db.iterdump()), database_before)
        self.assertEqual(world.digest(), before)

    def test_checkpoint_restore_then_archive_view_and_continuation(self):
        from history_archive import export_history
        from sqlite_history import SQLiteHistoryLedger
        from checkpoint_publication import publish_checkpoint, recover_checkpoint
        from archive_recovery import load_verified_checkpoint
        world = world_with_knowledge()
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "world.json"
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                export_history(world, ledger)
                publish_checkpoint(world, ledger, checkpoint)
                restored = recover_checkpoint(ledger, checkpoint)
                self.assertEqual(load_verified_checkpoint(checkpoint, ledger, audit_knowledge=True).digest(), world.digest())
                with archived_mapping(restored, ledger):
                    self.assertEqual(to_wire(character_view(restored, 1)), to_wire(character_view(world, 1)))
                    self.assertEqual(to_wire(observer_view(restored)), to_wire(observer_view(world)))
                restored.advance(10)
                world.advance(10)
                self.assertEqual(restored.digest(), world.digest())

    def test_archived_claim_does_not_reveal_unwitnessed_event_truth(self):
        from history_archive import export_history
        from sqlite_history import SQLiteHistoryLedger
        world = world_with_knowledge()
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                export_history(world, ledger)
                with archived_mapping(world, ledger):
                    wire = to_wire(character_view(world, 2))
                    self.assertNotIn("private historical truth", json.dumps(wire))
                    self.assertEqual(wire["remembered_events"], [])
                    self.assertEqual(wire["heard_claims"][0]["proposition"], "A disputed story")
                    self.assertEqual(wire["beliefs"][0]["proposition"], "Possibly true")

    def test_read_only_historical_windows_do_not_change_current_world(self):
        from history_archive import export_history
        from historical_window import HistoricalEventWindow
        from sqlite_history import SQLiteHistoryLedger
        world = world_with_knowledge()
        before = world.digest()
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                export_history(world, ledger)
                past, present = HistoricalEventWindow(ledger, 2), HistoricalEventWindow(ledger, 2)
                self.assertTrue(past.events(0, 0, limit=2))
                present.events(2, 10, limit=2)
                character_view(world, 1)
                observer_view(world)
                self.assertEqual(world.digest(), before)
                self.assertEqual(ledger.cursor(), (2, 3))


if __name__ == "__main__":
    unittest.main()
