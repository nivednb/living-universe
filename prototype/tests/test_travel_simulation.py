import unittest
from borders import BorderWorld, Route, Traveler
from history import HistoricalLedger
from world_state import Settlement, WorldState
from travel_simulation import TravelSimulation

class IntegratedTravelTests(unittest.TestCase):
    def setUp(self):
        borders = BorderWorld()
        borders.add_route(Route("cultivation", "nexus", 5, hazard=20, restriction=30))
        state = WorldState()
        state.add_settlement(Settlement("sect", "cultivation"))
        state.add_settlement(Settlement("crossroads", "nexus"))
        self.ledger = HistoricalLedger()
        self.sim = TravelSimulation(borders, state, self.ledger)
        self.state = state
        self.traveler = Traveler(7, "cultivation", 10, 50, 50, {("cultivation", "nexus")})
        self.sim.register(self.traveler, "sect")

    def test_arrival_only_after_travel_time(self):
        result = self.sim.depart(7, "nexus", "crossroads")
        self.assertTrue(result.accepted)
        self.assertNotIn(7, self.state.settlements["sect"].residents)
        self.assertNotIn(7, self.state.settlements["crossroads"].residents)
        self.assertEqual(self.traveler.region, "cultivation")
        self.sim.advance(4)
        self.assertNotIn(7, self.state.settlements["crossroads"].residents)
        self.sim.advance(1)
        self.assertEqual(self.traveler.region, "nexus")
        self.assertIn(7, self.state.settlements["crossroads"].residents)
        self.assertEqual(self.traveler.supplies, 5)
        self.assertEqual(len(self.ledger.events), 2)

    def test_traveler_witnesses_own_history_not_everyone(self):
        self.sim.depart(7, "nexus", "crossroads")
        self.sim.advance(5)
        self.assertTrue(self.ledger.knows(7, "travel-0"))
        self.assertTrue(self.ledger.knows(7, "travel-1"))
        self.assertFalse(self.ledger.knows(8, "travel-1"))

    def test_rejected_departure_preserves_residence(self):
        self.traveler.known_routes.clear()
        result = self.sim.depart(7, "nexus", "crossroads")
        self.assertFalse(result.accepted)
        self.assertIn(7, self.state.settlements["sect"].residents)
        self.assertEqual(self.traveler.supplies, 10)
        self.assertEqual(len(self.ledger.events), 0)

    def test_duplicate_departure_rejected(self):
        self.sim.depart(7, "nexus", "crossroads")
        with self.assertRaises(ValueError):
            self.sim.depart(7, "nexus", "crossroads")

    def test_invalid_time_rejected(self):
        with self.assertRaises(ValueError):
            self.sim.advance(-1)

if __name__ == "__main__":
    unittest.main()
