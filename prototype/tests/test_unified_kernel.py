import unittest
from borders import Route, Traveler
from discovery import Researcher, Technique
from world_state import Settlement
from unified_kernel import UnifiedKernel

def make_world(seed=42, destiny=0):
    world = UnifiedKernel(seed)
    world.add_settlement(Settlement("sect", "cultivation"))
    world.add_settlement(Settlement("nexus-town", "nexus"))
    world.add_route(Route("cultivation", "nexus", 5, 20, 30))
    world.add_technique(Technique("calculus", frozenset({"science"}), difficulty=1))
    world.add_technique(Technique("qi", frozenset({"cultivation"}), difficulty=1))
    world.add_technique(Technique("hybrid", frozenset({"science", "cultivation"}), frozenset({"calculus", "qi"}), 8))
    world.add_character(Traveler(1, "cultivation", 20, 80, 70, {("cultivation", "nexus")}),
                        Researcher(1, {"calculus", "qi"}, {"science": 5, "cultivation": 4}), "sect", destiny)
    return world

class UnifiedKernelTests(unittest.TestCase):
    def test_journey_and_research_share_one_clock_and_history(self):
        world = make_world()
        world.depart(1, "nexus-town")
        world.research(1, "hybrid", 3)
        world.advance(3)
        self.assertEqual(world.locations.get(1), None)
        self.assertEqual(len(world.outcomes), 1)
        world.advance(2)
        self.assertEqual(world.locations[1], "nexus-town")
        self.assertEqual(world.travelers[1].region, "nexus")
        self.assertEqual([e.year for e in world.history.events.values()], [0, 0, 3, 5])

    def test_reproducible_across_incremental_advance(self):
        a, b = make_world(), make_world()
        for world in (a, b):
            world.depart(1, "nexus-town")
            world.research(1, "hybrid", 3)
        a.advance(5)
        b.advance(2)
        b.advance(3)
        self.assertEqual(a.digest(), b.digest())

    def test_destiny_changes_probability_not_guaranteed_outcome(self):
        lucky = make_world(1, 100)
        unlucky = make_world(1, -100)
        for world in (lucky, unlucky):
            world.research(1, "hybrid", 1)
            world.advance(1)
        self.assertGreater(lucky.outcomes[0][5], unlucky.outcomes[0][5])
        self.assertEqual(lucky.outcomes[0][4], unlucky.outcomes[0][4])
        self.assertLessEqual(lucky.outcomes[0][5], 95)
        self.assertGreaterEqual(unlucky.outcomes[0][5], 5)

    def test_unwitnessed_history_not_known(self):
        world = make_world()
        world.research(1, "hybrid", 1)
        world.advance(1)
        self.assertTrue(world.history.knows(1, "kernel-1"))
        self.assertFalse(world.history.knows(999, "kernel-1"))

    def test_rejected_travel_preserves_residence(self):
        world = make_world()
        world.travelers[1].known_routes.clear()
        self.assertFalse(world.depart(1, "nexus-town").accepted)
        self.assertIn(1, world.state.settlements["sect"].residents)

if __name__ == "__main__":
    unittest.main()
