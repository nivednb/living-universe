import unittest
from discovery import DiscoveryWorld, Researcher, Technique
from history import HistoricalLedger
from research_simulation import ResearchSimulation

class ResearchSimulationTests(unittest.TestCase):
    def setUp(self):
        world = DiscoveryWorld()
        world.add_technique(Technique("calculus", frozenset({"science"}), difficulty=1))
        world.add_technique(Technique("qi", frozenset({"cultivation"}), difficulty=1))
        world.add_technique(Technique("hybrid", frozenset({"science", "cultivation"}), frozenset({"calculus", "qi"}), 8))
        world.add_researcher(Researcher(1, {"calculus", "qi"}, {"science": 5, "cultivation": 4}))
        world.add_researcher(Researcher(2))
        self.world = world
        self.ledger = HistoricalLedger()
        self.sim = ResearchSimulation(world, self.ledger)

    def test_discovery_occurs_only_on_completion(self):
        self.sim.schedule(1, "hybrid", 10)
        self.sim.advance(9)
        self.assertNotIn("hybrid", self.world.researchers[1].knowledge)
        self.sim.advance(1)
        self.assertIn("hybrid", self.world.researchers[1].knowledge)
        self.assertTrue(self.ledger.knows(1, "research-0"))
        self.assertFalse(self.ledger.knows(2, "research-0"))

    def test_teaching_requires_discovery_and_records_witnesses(self):
        self.assertFalse(self.sim.teach(1, 2, "hybrid"))
        self.sim.schedule(1, "hybrid", 2)
        self.sim.advance(2)
        self.assertTrue(self.sim.teach(1, 2, "hybrid"))
        self.assertIn("hybrid", self.world.researchers[2].knowledge)
        self.assertTrue(self.ledger.knows(2, "research-1"))

    def test_failed_research_still_becomes_history(self):
        self.world.researchers[1].expertise["science"] = 0
        self.sim.schedule(1, "hybrid", 3)
        self.sim.advance(3)
        self.assertNotIn("hybrid", self.world.researchers[1].knowledge)
        self.assertEqual(self.sim.outcomes, [(3, 1, "hybrid", False)])
        self.assertIn("research-0", self.ledger.events)

    def test_duplicate_research_rejected(self):
        self.sim.schedule(1, "hybrid", 5)
        with self.assertRaises(ValueError):
            self.sim.schedule(1, "hybrid", 5)

    def test_invalid_duration_rejected(self):
        with self.assertRaises(ValueError):
            self.sim.schedule(1, "hybrid", 0)

if __name__ == "__main__":
    unittest.main()
