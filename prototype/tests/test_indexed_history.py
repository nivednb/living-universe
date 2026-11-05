"""Indexed historical event lookup and migration regressions."""
import tempfile
import unittest
from pathlib import Path

from sqlite_history import SQLiteHistoryLedger, HistoryIntegrityError


class IndexedHistoryTests(unittest.TestCase):
    def test_indexed_lookup_and_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.sqlite"
            with SQLiteHistoryLedger(path) as ledger:
                ledger.append_many((i, i, "historical_event", None,
                                    {"id": f"e-{i}", "description": str(i), "witnesses": []})
                                   for i in range(100))
                self.assertEqual(ledger.get_event_by_id("e-70")[0], 70)
                self.assertIsNone(ledger.get_event_by_id("missing"))
                with self.assertRaises(Exception):
                    ledger.append_many([(100, 100, "historical_event", None,
                                         {"id": "e-70", "description": "duplicate", "witnesses": []})])
                self.assertEqual(ledger.cursor(), (99, 100))
            with SQLiteHistoryLedger(path) as ledger:
                self.assertEqual(ledger.get_event_by_id("e-70")[4]["id"], "e-70")

    def test_streamed_audit_detects_duplicate_payload_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                ledger.append_many([
                    (0, 0, "historical_event", None,
                     {"id": "a", "description": "first", "witnesses": []}),
                    (1, 1, "historical_event", None,
                     {"id": "b", "description": "second", "witnesses": []}),
                ])
                self.assertEqual(ledger.check_event_id_index(), 2)
                # Change the canonical row AND digest to mimic a validly
                # re-encoded event whose ID index was not updated.
                import hashlib
                import json
                payload = {"id": "a", "description": "second", "witnesses": []}
                body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                digest = hashlib.sha256(
                    json.dumps([1, 1, "historical_event", None, payload],
                               sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
                ).hexdigest()
                ledger.db.execute(
                    "UPDATE events SET payload=?,digest=? WHERE sequence=1",
                    (body, digest),
                )
                ledger.db.commit()
                with self.assertRaises(HistoryIntegrityError):
                    ledger.check_event_id_index()

    def test_wrong_index_mapping_detected_even_when_counts_match(self):
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                ledger.append_many([
                    (0, 0, "historical_event", None,
                     {"id": "a", "description": "first", "witnesses": []}),
                    (1, 1, "historical_event", None,
                     {"id": "b", "description": "second", "witnesses": []}),
                ])
                ledger.db.execute("UPDATE event_ids SET sequence=9 WHERE event_id='a'")
                ledger.db.commit()
                with self.assertRaises(HistoryIntegrityError):
                    ledger.get_event_by_id("a")
                self.assertEqual(ledger.rebuild_event_id_index(), 2)
                self.assertEqual(ledger.get_event_by_id("a")[0], 0)

    def test_batched_rebuild_and_atomic_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                ledger.append_many(
                    (i, i, "historical_event", None,
                     {"id": f"id-{i}", "description": str(i), "witnesses": []})
                    for i in range(7)
                )
                ledger.db.execute("DELETE FROM event_ids")
                ledger.db.commit()
                self.assertEqual(ledger.rebuild_event_id_index(batch_size=2), 7)
                self.assertEqual(ledger.get_event_by_id("id-6")[0], 6)
                # Corrupt an event after index creation: rebuild must fail,
                # preserving the pre-rebuild mappings by rollback.
                ledger.db.execute("UPDATE events SET payload='{}' WHERE sequence=3")
                ledger.db.commit()
                before = ledger.db.execute(
                    "SELECT event_id,sequence FROM event_ids ORDER BY sequence"
                ).fetchall()
                with self.assertRaises(HistoryIntegrityError):
                    ledger.rebuild_event_id_index(batch_size=2)
                after = ledger.db.execute(
                    "SELECT event_id,sequence FROM event_ids ORDER BY sequence"
                ).fetchall()
                self.assertEqual(after, before)

    def test_explicit_legacy_index_rebuild(self):
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                ledger.append_many([(0, 0, "historical_event", None,
                                     {"id": "old", "description": "old", "witnesses": []})])
                ledger.db.execute("DELETE FROM event_ids")
                ledger.db.commit()
                with self.assertRaises(HistoryIntegrityError):
                    ledger.get_event_by_id("old")
                self.assertEqual(ledger.rebuild_event_id_index(), 1)
                self.assertEqual(ledger.get_event_by_id("old")[0], 0)


if __name__ == "__main__":
    unittest.main()
