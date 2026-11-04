import unittest
from power_ceiling import ActorPower, EngineCapabilities, evaluate

class PowerCeilingTests(unittest.TestCase):
    def test_engine_upgrade_does_not_grant_power(self):
        actor = ActorPower(1, {"regional_ward"})
        upgraded = EngineCapabilities(2, frozenset({"regional_ward", "timeline_branch"}))
        self.assertFalse(evaluate(actor, "timeline_branch", upgraded).permitted)

    def test_unsupported_ability_remains_known_but_not_executed(self):
        actor = ActorPower(1, {"timeline_branch"})
        basic = EngineCapabilities(1, frozenset({"regional_ward"}))
        result = evaluate(actor, "timeline_branch", basic)
        self.assertFalse(result.permitted)
        self.assertEqual(result.reason, "unsupported_by_engine")
        self.assertEqual(result.fidelity, "abstract")

    def test_upgrade_enables_existing_ability(self):
        actor = ActorPower(1, {"timeline_branch"})
        upgraded = EngineCapabilities(2, frozenset({"timeline_branch"}))
        self.assertTrue(evaluate(actor, "timeline_branch", upgraded).permitted)

    def test_unlocked_supported_ability(self):
        actor = ActorPower(1, {"regional_ward"})
        engine = EngineCapabilities(1, frozenset({"regional_ward"}))
        self.assertTrue(evaluate(actor, "regional_ward", engine).permitted)

if __name__ == "__main__":
    unittest.main()
