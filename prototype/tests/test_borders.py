import unittest
from borders import BorderWorld, Route, Traveler

class BorderTests(unittest.TestCase):
    def setUp(self):
        self.world = BorderWorld()
        self.world.add_route(Route("cultivation", "nexus", 12, hazard=40, restriction=60))

    def test_unknown_route_prevents_omniscient_travel(self):
        traveler = Traveler(1, "cultivation", 20, 100, 100)
        self.assertEqual(self.world.travel(traveler, "nexus").reason, "unknown_route")
        self.assertEqual(traveler.region, "cultivation")

    def test_restriction_prevents_travel(self):
        traveler = Traveler(1, "cultivation", 20, 100, 30, {("cultivation", "nexus")})
        self.assertEqual(self.world.travel(traveler, "nexus").reason, "restricted")
        self.assertEqual(traveler.supplies, 20)

    def test_success_consumes_supplies(self):
        traveler = Traveler(1, "cultivation", 20, 80, 70, {("cultivation", "nexus")})
        self.assertTrue(self.world.travel(traveler, "nexus").accepted)
        self.assertEqual((traveler.region, traveler.supplies), ("nexus", 8))

    def test_hazard_prevents_travel(self):
        traveler = Traveler(1, "cultivation", 20, 20, 70, {("cultivation", "nexus")})
        self.assertEqual(self.world.travel(traveler, "nexus").reason, "hazard")

    def test_no_teleport_without_route(self):
        traveler = Traveler(1, "cultivation", 20, 100, 100, {("cultivation", "magic")})
        self.assertEqual(self.world.travel(traveler, "magic").reason, "no_route")

if __name__ == "__main__":
    unittest.main()
