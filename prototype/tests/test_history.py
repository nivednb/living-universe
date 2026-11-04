import unittest
from history import Claim, Event, HistoricalLedger

class HistoricalLedgerTests(unittest.TestCase):
    def test_witness_access_not_omniscient(self):
        ledger = HistoricalLedger()
        ledger.record(Event("e1", -100000, "Ancient observatory destroyed", frozenset({7})))
        self.assertTrue(ledger.knows(7, "e1"))
        self.assertFalse(ledger.knows(8, "e1"))

    def test_rumor_is_not_world_truth(self):
        ledger = HistoricalLedger()
        ledger.record(Event("e1", -100000, "Ancient observatory destroyed"))
        ledger.publish_claim(Claim("c1", "e1", "A dragon destroyed the observatory", "oral tradition"))
        ledger.communicate("c1", 8)
        self.assertTrue(ledger.knows(8, "c1"))
        self.assertFalse(ledger.knows(8, "e1"))
        self.assertEqual(ledger.events["e1"].description, "Ancient observatory destroyed")

    def test_duplicate_events_rejected(self):
        ledger = HistoricalLedger()
        ledger.record(Event("e1", -100000, "Founding"))
        with self.assertRaises(ValueError):
            ledger.record(Event("e1", -100000, "Other"))

    def test_negative_years_supported(self):
        ledger = HistoricalLedger()
        ledger.record(Event("primordial", -(10**10), "Primordial epoch"))
        self.assertEqual(ledger.events["primordial"].year, -(10**10))

if __name__ == "__main__":
    unittest.main()
