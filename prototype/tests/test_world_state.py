import unittest
from world_state import KnowledgeClaim, Settlement, WorldState

class WorldStateTests(unittest.TestCase):
    def setUp(self):
        self.world = WorldState()
        self.world.add_settlement(Settlement("sect", "cultivation", {"grain": 100}))
        self.world.add_settlement(Settlement("town", "science", {"grain": 20}))

    def test_transfer_conserves_resources(self):
        self.world.transfer("sect", "town", "grain", 30)
        self.assertEqual(self.world.settlements["sect"].resources["grain"], 70)
        self.assertEqual(self.world.settlements["town"].resources["grain"], 50)

    def test_insufficient_transfer_is_atomic(self):
        with self.assertRaises(ValueError):
            self.world.transfer("sect", "town", "grain", 101)
        self.assertEqual(self.world.settlements["sect"].resources["grain"], 100)
        self.assertEqual(self.world.settlements["town"].resources["grain"], 20)

    def test_unknown_claim_rejected(self):
        with self.assertRaises(KeyError):
            self.world.learn(7, "unknown")

    def test_beliefs_are_not_global_truth(self):
        claim = KnowledgeClaim("c1", "A vanished master created the first technique", "event-12")
        self.world.add_claim(claim)
        self.world.learn(7, "c1")
        self.assertIn("c1", self.world.beliefs[7])
        self.assertNotIn(8, self.world.beliefs)

    def test_invalid_resource_quantities_rejected(self):
        with self.assertRaises(ValueError):
            Settlement("bad", "magic", {"grain": -1})
