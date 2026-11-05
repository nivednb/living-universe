"""Archive-backed epistemic reference resolution tests."""
import tempfile
import unittest
from pathlib import Path

from archive_references import ArchivedReferenceResolver
from history import Claim
from sqlite_history import SQLiteHistoryLedger


class ArchivedReferenceTests(unittest.TestCase):
    def test_claim_and_knowledge_resolution(self):
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "events.sqlite") as ledger:
                ledger.append_many([(0, 0, "historical_event", None,
                                     {"id": "event-0", "year": 0,
                                      "description": "A witness saw it", "witnesses": [7]})])
                claims = {"claim-0": Claim("claim-0", "event-0", "It happened", "7")}
                resolver = ArchivedReferenceResolver(ledger, claims)
                self.assertTrue(resolver.event_exists("event-0"))
                self.assertFalse(resolver.event_exists("missing"))
                self.assertTrue(resolver.reference_exists("claim-0"))
                self.assertEqual(resolver.resolve_claim_event("claim-0").id, "event-0")
                self.assertTrue(resolver.knows({7: {"event-0"}}, 7, "event-0"))
                self.assertFalse(resolver.knows({7: {"missing"}}, 7, "missing"))
                self.assertEqual(resolver.validate_claim_references(), 1)

    def test_missing_claim_target_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "events.sqlite") as ledger:
                resolver = ArchivedReferenceResolver(
                    ledger, {"claim-0": Claim("claim-0", "absent", "False", "7")}
                )
                with self.assertRaises(ValueError):
                    resolver.validate_claim_references()


if __name__ == "__main__":
    unittest.main()
