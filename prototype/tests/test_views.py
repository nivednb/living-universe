from dataclasses import FrozenInstanceError
import json
import unittest

from history import Claim, Event
from unified_persistence import decode, encode
from views import character_view, observer_view, to_wire
from world_state import KnowledgeClaim
from test_unified_persistence import make_world


class ViewTests(unittest.TestCase):
    def test_no_viewer_and_multiple_viewers_produce_same_world(self):
        headless, watched = make_world(), make_world()
        for world in (headless, watched):
            world.depart(1, "market")
            world.research(1, "hybrid", 5)
        for _ in range(10):
            before = watched.digest()
            for selection in (None, [], [1], [2], [2, 1]):
                to_wire(observer_view(watched, actor_ids=selection))
            for actor in (1, 2):
                to_wire(character_view(watched, actor))
            self.assertEqual(before, watched.digest())
            headless.advance(1)
            watched.advance(1)
        self.assertEqual(headless.digest(), watched.digest())

    def test_views_are_detached_and_immutable(self):
        world = make_world()
        view = observer_view(world)
        before = world.digest()
        with self.assertRaises(FrozenInstanceError):
            view.actors[0].region = "science"
        with self.assertRaises(TypeError):
            view.settlements[0].resources[0] = ("food", 0)
        wire = to_wire(view)
        wire["settlements"][0]["resources"].clear()
        wire["actors"].clear()
        self.assertEqual(before, world.digest())
        world.depart(1, "market")
        world.advance(5)
        self.assertEqual(view.day, 0)
        self.assertEqual(view.actors[0].settlement_id, "sect")
        self.assertEqual(observer_view(world).actors[0].settlement_id, "market")

    def test_character_cannot_read_unwitnessed_truth_or_evidence(self):
        world = make_world()
        world.history.record(Event("hidden", -10, "SECRET_TRUTH", frozenset({1})))
        world.history.record(Event("SECRET_EVIDENCE", -9, "A private source", frozenset({1})))
        world.history.publish_claim(Claim("rumor", "hidden", "A disputed account", "archive"))
        world.history.communicate("rumor", 2)
        world.state.add_claim(KnowledgeClaim("belief", "Possibly so", "hidden", ("SECRET_EVIDENCE",)))
        world.state.learn(2, "belief")
        world.validate()
        view = character_view(world, 2)
        wire = to_wire(view)
        self.assertEqual(view.remembered_events, ())
        self.assertEqual(view.heard_claims[0].proposition, "A disputed account")
        self.assertEqual(view.beliefs[0].proposition, "Possibly so")
        self.assertNotIn("SECRET", json.dumps(wire))
        self.assertNotIn("hidden", json.dumps(wire))
        self.assertEqual(wire["actor"]["id"], 2)
        self.assertEqual(view.techniques, ("math",))
        self.assertIn("SECRET_TRUTH", [e.description for e in character_view(world, 1).remembered_events])

    def test_no_checkpoint_secrets_in_wire_messages(self):
        world = make_world()
        for view in (observer_view(world), character_view(world, 1)):
            wire = to_wire(view)
            self.assertEqual(wire["version"], 1)
            for key in ("rng", "seed", "destiny", "outcomes", "pending", "sequence", "rules_version"):
                self.assertNotIn(key, wire)
        self.assertEqual(to_wire(observer_view(world))["scope"], "observer")
        self.assertEqual(to_wire(character_view(world, 1))["scope"], "character")
        with self.assertRaises(TypeError):
            to_wire(encode(world))

    def test_transit_and_arrival_use_authoritative_day(self):
        world = make_world()
        world.depart(1, "market")
        world.advance(2)
        view = character_view(world, 1)
        self.assertEqual(view.day, 2)
        self.assertIsNone(view.actor.settlement_id)
        self.assertEqual(view.actor.destination_id, "market")
        self.assertEqual(view.actor.arrival_day, 5)
        self.assertEqual(view.actor.region, "cultivation")
        world.advance(3)
        actor = character_view(world, 1).actor
        self.assertEqual(actor.settlement_id, "market")
        self.assertEqual(actor.region, "nexus")
        self.assertIsNone(actor.arrival_day)
        self.assertIsNone(actor.destination_id)

    def test_view_roundtrip_is_stable_through_checkpoint(self):
        world = make_world()
        world.depart(1, "market")
        world.research(1, "hybrid", 5)
        world.advance(2)
        restored = decode(encode(world))
        self.assertEqual(to_wire(observer_view(world)), to_wire(observer_view(restored)))
        for actor in (1, 2):
            self.assertEqual(to_wire(character_view(world, actor)), to_wire(character_view(restored, actor)))

    def test_selection_order_is_stable_and_invalid_ids_fail_without_mutation(self):
        world = make_world()
        self.assertEqual(observer_view(world, actor_ids=[2, 1, 2]), observer_view(world))
        self.assertEqual(observer_view(world, actor_ids=[]).actors, ())
        before = world.digest()
        for actor in (True, -1, 999, "1", None):
            with self.assertRaises(ValueError):
                character_view(world, actor)
            with self.assertRaises(ValueError):
                observer_view(world, actor_ids=[actor])
        for selection in ([1, True], [1, 1.0], [[]]):
            with self.assertRaises(ValueError):
                observer_view(world, actor_ids=selection)
        self.assertEqual(world.digest(), before)


if __name__ == "__main__":
    unittest.main()
