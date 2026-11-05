"""Viewer-side mutation attempts against detached, frozen read models."""
from dataclasses import fields, is_dataclass
import unittest

from test_unified_persistence import make_world
from views import character_view, observer_view, to_wire


class ViewAuditTests(unittest.TestCase):
    def test_views_contain_only_detached_values_and_no_kernel_capability(self):
        world = make_world()
        world.research(1, "hybrid", 3)
        before = world.digest()

        def inspect(value):
            if type(value) in (int, str, type(None)):
                return
            if isinstance(value, tuple):
                for item in value:
                    inspect(item)
                return
            self.assertTrue(is_dataclass(value))
            self.assertTrue(value.__dataclass_params__.frozen)
            for field in fields(value):
                inspect(getattr(value, field.name))

        for view in (observer_view(world), character_view(world, 1)):
            inspect(view)
            for name in ("advance", "research", "depart", "rng", "pending", "history", "world", "ledger"):
                self.assertFalse(hasattr(view, name))
            # Python's object API can bypass frozen dataclasses. It can alter
            # only the detached view, never the world or its RNG/event queue.
            object.__setattr__(view, "day", -999)
            if hasattr(view, "actor"):
                view.actor.__dict__["region"] = "malicious local display value"
            else:
                view.actors[0].__dict__["region"] = "malicious local display value"
        self.assertEqual(world.digest(), before)

    def test_old_character_view_does_not_change_after_successful_discovery(self):
        world = make_world()
        world.rng.seed(1)
        world.research(1, "hybrid", 1)
        view = character_view(world, 1)
        original = to_wire(view)
        attacker_message = to_wire(view)
        attacker_message["actor"]["id"] = 999
        attacker_message["techniques"].append("invented")
        attacker_message["remembered_events"][0]["description"] = "invented"
        before = world.digest()
        self.assertEqual(to_wire(view), original)
        self.assertEqual(world.digest(), before)
        world.advance(1)
        self.assertTrue(world.outcomes[-1][3])
        self.assertEqual(to_wire(view), original)
        self.assertNotIn("hybrid", view.techniques)
        self.assertIn("hybrid", character_view(world, 1).techniques)


if __name__ == "__main__":
    unittest.main()
