import unittest
from discovery import DiscoveryWorld, Researcher, Technique

class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.world = DiscoveryWorld()
        self.world.add_technique(Technique("calculus", frozenset({"science"}), difficulty=1))
        self.world.add_technique(Technique("qi_control", frozenset({"cultivation"}), difficulty=1))
        self.world.add_technique(Technique("optimized_qi", frozenset({"science", "cultivation"}), frozenset({"calculus", "qi_control"}), 8))
        self.world.add_researcher(Researcher(1, {"calculus", "qi_control"}, {"science": 5, "cultivation": 4}))
        self.world.add_researcher(Researcher(2))

    def test_interdisciplinary_discovery(self):
        self.assertTrue(self.world.discover(1, "optimized_qi"))
        self.assertEqual(self.world.discoveries[0].source_knowledge, ("calculus", "qi_control"))

    def test_missing_prerequisites(self):
        self.world.researchers[1].knowledge.remove("calculus")
        self.assertFalse(self.world.discover(1, "optimized_qi"))

    def test_insufficient_expertise(self):
        self.world.researchers[1].expertise["science"] = 0
        self.assertFalse(self.world.discover(1, "optimized_qi"))

    def test_knowledge_is_not_global(self):
        self.world.discover(1, "optimized_qi")
        self.assertNotIn("optimized_qi", self.world.researchers[2].knowledge)
        self.assertTrue(self.world.teach(1, 2, "optimized_qi"))
        self.assertIn("optimized_qi", self.world.researchers[2].knowledge)

    def test_uninformed_teacher_cannot_transmit(self):
        self.assertFalse(self.world.teach(2, 1, "optimized_qi"))

if __name__ == "__main__":
    unittest.main()
