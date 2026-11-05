"""Independent integration-audit regressions; no simulation rules changes."""
import hashlib
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from archive_writer import ArchivedEventWriter
from atomic_witness_archive import append_event_with_witnesses, verify_witness_memory
from checkpoint_publication import publish_checkpoint, recover_checkpoint
from history import Event
from history_archive import export_history, verify_history
from sqlite_history import HistoryIntegrityError, SQLiteHistoryLedger, _canonical
from test_unified_persistence import make_world


def recorded_world():
    world = make_world()
    world.history.record(Event("ancient", -100, "Before the epoch", frozenset({1})))
    world.research(1, "hybrid", 3)
    return world


def record(event_id="next", sequence=1):
    return (sequence, sequence, "historical_event", None,
            {"id": event_id, "year": sequence, "description": "An event", "witnesses": [1, 2]})


def rows(ledger):
    return tuple(tuple(ledger.db.execute("SELECT * FROM " + table + " ORDER BY 1,2"))
                 for table in ("events", "event_ids", "event_witness_memory"))


class ArchiveAuditTests(unittest.TestCase):
    def test_all_three_tables_rollback_at_each_insert_stage_and_reopen(self):
        for table, condition in (("events", "NEW.sequence=1"), ("event_ids", "NEW.event_id='next'"),
                                 ("event_witness_memory", "NEW.actor=2")):
            with self.subTest(table=table), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "history.sqlite"
                with SQLiteHistoryLedger(path) as ledger:
                    append_event_with_witnesses(ledger, Event("first", 0, "First", frozenset({1})))
                    before = rows(ledger)
                    ledger.db.execute(f"CREATE TRIGGER injected BEFORE INSERT ON {table} "
                                      f"WHEN {condition} BEGIN SELECT RAISE(ABORT,'injected'); END")
                    with self.assertRaises(sqlite3.IntegrityError):
                        ledger.append_many([record()], witness_rows=[("next", 1), ("next", 2)])
                    self.assertEqual(rows(ledger), before)
                with SQLiteHistoryLedger(path) as ledger:
                    self.assertEqual(rows(ledger), before)
                    self.assertEqual(verify_witness_memory(ledger), 1)

    def test_invalid_or_inconsistent_witness_rows_rejected_before_writes(self):
        bad_rows = [[("next", True)], [("next", 1.5)], [("next", "1")], [("next", -1)],
                    [("next", 2**63)], [("ghost", 1)], [("next", 1)], [],
                    [("next", 1), ("next", 1), ("next", 2)]]
        for witnesses in bad_rows:
            with self.subTest(witnesses=witnesses), tempfile.TemporaryDirectory() as directory:
                with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                    append_event_with_witnesses(ledger, Event("first", 0, "First", frozenset({1})))
                    before = rows(ledger)
                    with self.assertRaises(ValueError):
                        ledger.append_many([record()], witness_rows=witnesses)
                    self.assertEqual(rows(ledger), before)

    def test_nonempty_legacy_archive_is_not_implicitly_upgraded(self):
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                ledger.append_many([record("old", 0)])
                with self.assertRaises(HistoryIntegrityError):
                    append_event_with_witnesses(ledger, Event("next", 1, "Next", frozenset({1})))
                self.assertEqual(ledger.cursor(), (0, 1))
                self.assertIsNone(ledger.db.execute(
                    "SELECT 1 FROM sqlite_master WHERE name='event_witness_memory'").fetchone())

    def test_witness_corruption_matrix_after_reopen(self):
        corruptions = ["DELETE FROM event_witness_memory WHERE event_id='first'",
                       "INSERT INTO event_witness_memory VALUES('first',9)",
                       "INSERT INTO event_witness_memory VALUES('orphan',9)",
                       "UPDATE event_witness_memory SET actor=3 WHERE event_id='first'",
                       "UPDATE event_witness_memory SET actor=CASE actor WHEN 1 THEN 2 ELSE 1 END",
                       "DELETE FROM event_ids WHERE event_id='first'",
                       "UPDATE event_ids SET sequence=9 WHERE event_id='first'",
                       "UPDATE events SET payload='{}' WHERE sequence=0",
                       "DROP TABLE event_witness_memory"]
        for corruption in corruptions:
            with self.subTest(corruption=corruption), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "history.sqlite"
                with SQLiteHistoryLedger(path) as ledger:
                    append_event_with_witnesses(ledger, Event("first", 0, "First", frozenset({1})))
                    append_event_with_witnesses(ledger, Event("second", 1, "Second", frozenset({2})))
                    ledger.db.execute(corruption)
                    ledger.db.commit()
                with SQLiteHistoryLedger(path) as ledger:
                    with self.assertRaises(HistoryIntegrityError):
                        verify_witness_memory(ledger)

    def test_legacy_mirror_cannot_be_published_without_witness_persistence(self):
        world = recorded_world()
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "world.json"
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                export_history(world, ledger)
                ledger.db.execute("DROP TABLE event_witness_memory")
                ledger.db.commit()
                with self.assertRaises(HistoryIntegrityError):
                    publish_checkpoint(world, ledger, checkpoint)
                self.assertFalse(checkpoint.exists())
                self.assertEqual(ledger.cursor(), (1, 2))

    def test_duplicate_event_id_preserves_all_three_tables_after_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.sqlite"
            with SQLiteHistoryLedger(path) as ledger:
                append_event_with_witnesses(ledger, Event("first", 0, "First", frozenset({1})))
                before = rows(ledger)
                with self.assertRaises(sqlite3.IntegrityError):
                    append_event_with_witnesses(ledger, Event("first", 1, "Duplicate", frozenset({2})))
                self.assertEqual(rows(ledger), before)
            with SQLiteHistoryLedger(path) as ledger:
                self.assertEqual(rows(ledger), before)

    def test_witness_enabled_archive_cannot_append_without_memories(self):
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                append_event_with_witnesses(ledger, Event("first", 0, "First"))
                before = rows(ledger)
                with self.assertRaises(ValueError):
                    ledger.append_many([record()])
                with self.assertRaises(ValueError):
                    ledger.append_many([], witness_rows=[("ghost", 1)])
                self.assertEqual(rows(ledger), before)

    def test_sequence_day_and_signed_year_contracts(self):
        from archived_events import ArchivedEvents
        world = recorded_world()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.sqlite"
            with SQLiteHistoryLedger(path) as ledger:
                export_history(world, ledger)
                with self.assertRaises(ValueError):
                    ledger.append_many([(2, -1, "other", None, {})])
            with SQLiteHistoryLedger(path) as ledger:
                self.assertEqual(ArchivedEvents(ledger)["ancient"].year, -100)
                self.assertEqual([r[0] for r in ledger.iter_events()], [0, 1])
                self.assertEqual(verify_history(world, ledger), 2)
            with SQLiteHistoryLedger(Path(directory) / "sparse.sqlite") as ledger:
                ledger.append_many([record("a", 0), record("b", 2)])
                with self.assertRaises(HistoryIntegrityError):
                    ArchivedEventWriter(ledger).record_kernel(3, "arrival", 1, "Village")
                self.assertEqual(ledger.cursor(), (2, 2))

    def test_json_key_aliasing_rejected_without_creating_unreadable_event(self):
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                with self.assertRaises((ValueError, TypeError)):
                    ledger.append_many([(0, 0, "other", None, {1: "integer", "1": "string"})])
                self.assertEqual(ledger.cursor(), (None, 0))

    def test_storage_apis_do_not_commit_callers_open_transaction(self):
        for operation in ("append", "publish", "recover"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as directory:
                world = recorded_world()
                checkpoint = Path(directory) / "world.json"
                with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                    export_history(world, ledger)
                    publish_checkpoint(world, ledger, checkpoint)
                    ledger.db.execute("CREATE TABLE unrelated(value INTEGER)")
                    ledger.db.execute("INSERT INTO unrelated VALUES(1)")
                    with self.assertRaises(HistoryIntegrityError):
                        if operation == "append":
                            ledger.append_many([record(sequence=2)], witness_rows=[("next", 1), ("next", 2)])
                        elif operation == "publish":
                            publish_checkpoint(world, ledger, checkpoint)
                        else:
                            recover_checkpoint(ledger, checkpoint)
                    self.assertTrue(ledger.db.in_transaction)
                    ledger.db.rollback()
                    self.assertEqual(ledger.db.execute("SELECT COUNT(*) FROM unrelated").fetchone()[0], 0)
                    self.assertEqual(ledger.cursor(), (1, 2))

    def test_witness_audit_checks_the_id_index_even_without_witnesses(self):
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                append_event_with_witnesses(ledger, Event("first", 0, "First"))
                ledger.db.execute("DELETE FROM event_ids")
                ledger.db.commit()
                with self.assertRaises(HistoryIntegrityError):
                    verify_witness_memory(ledger)

    def test_mirror_verification_checks_index_and_optional_witness_rows(self):
        for corruption in ("DELETE FROM event_ids", "DELETE FROM event_witness_memory"):
            with self.subTest(corruption=corruption), tempfile.TemporaryDirectory() as directory:
                world = recorded_world()
                with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                    for index, event in enumerate(world.history.events.values()):
                        ledger.append_many([(index, max(0, event.year), "historical_event", None,
                                             {"id": event.id, "year": event.year,
                                              "description": event.description,
                                              "witnesses": sorted(event.witnesses)})],
                                           witness_rows=[(event.id, a) for a in sorted(event.witnesses)])
                    ledger.db.execute(corruption)
                    ledger.db.commit()
                    with self.assertRaises(HistoryIntegrityError):
                        verify_history(world, ledger)

    def test_reencoded_invalid_payload_witnesses_fail_audit(self):
        for witnesses in ([True], [1.0], [1, 1], [-1], ["1"]):
            with self.subTest(witnesses=witnesses), tempfile.TemporaryDirectory() as directory:
                with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                    append_event_with_witnesses(ledger, Event("first", 0, "First", frozenset({1})))
                    payload = {"id": "first", "year": 0, "description": "First", "witnesses": witnesses}
                    digest = hashlib.sha256(_canonical([0, 0, "historical_event", None, payload]).encode()).hexdigest()
                    ledger.db.execute("UPDATE events SET payload=?,digest=?", (_canonical(payload), digest))
                    ledger.db.commit()
                    with self.assertRaises(HistoryIntegrityError):
                        verify_witness_memory(ledger)

    def test_writer_allocates_ids_like_kernel_after_seeded_events_and_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                writer = ArchivedEventWriter(ledger, reserved_claim_ids={"kernel-2"})
                writer.record(Event("kernel-1", 0, "Seeded history"))
                generated = writer.record_kernel(1, "arrival", 1, "Village")
                self.assertEqual(generated.id, "kernel-3")

    def test_generator_witnesses_are_not_consumed_during_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                event = ArchivedEventWriter(ledger).record_kernel(0, "arrival", 1, "Village", iter([1, 2]))
                self.assertEqual(event.witnesses, frozenset({1, 2}))

    def test_writer_matches_authoritative_recording_with_seeded_collisions(self):
        from history import Claim
        world = make_world()
        world.history.record(Event("kernel-1", 0, "Seeded history", frozenset({1})))
        world.history.publish_claim(Claim("kernel-2", "kernel-1", "A claim", "archive"))
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                export_history(world, ledger)
                writer = ArchivedEventWriter(ledger, world.history.claims)
                world.research(1, "hybrid", 1)
                event = writer.record_kernel(0, "research_start", 1, "Research began: hybrid")
                self.assertEqual(event, world.history.events["kernel-3"])
                self.assertEqual(verify_history(world, ledger), 2)

    def test_recovery_does_not_replace_old_checkpoint_before_archive_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            world = recorded_world()
            checkpoint = Path(directory) / "world.json"
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                export_history(world, ledger)
                publish_checkpoint(world, ledger, checkpoint)
                before = checkpoint.read_bytes()
                world.advance(1)
                with patch("checkpoint_publication.Path.replace", side_effect=OSError("crash before rename")):
                    with self.assertRaises(OSError):
                        publish_checkpoint(world, ledger, checkpoint)
                candidate = checkpoint.with_name(checkpoint.name + ".pending")
                prepared = candidate.read_bytes()
                ledger.db.execute("UPDATE events SET payload='{}' WHERE sequence=0")
                ledger.db.commit()
                with self.assertRaises(HistoryIntegrityError):
                    recover_checkpoint(ledger, checkpoint)
                self.assertEqual(checkpoint.read_bytes(), before)
                self.assertEqual(candidate.read_bytes(), prepared)
                self.assertEqual(ledger.db.execute("SELECT status FROM checkpoint_publication").fetchone()[0], "prepared")

    def test_recovery_syncs_directory_after_already_completed_rename(self):
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "world.json"
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                world = recorded_world()
                export_history(world, ledger)
                publish_checkpoint(world, ledger, checkpoint)
                ledger.db.execute("UPDATE checkpoint_publication SET status='prepared'")
                ledger.db.commit()
                with patch("checkpoint_publication._sync_directory") as sync:
                    recover_checkpoint(ledger, checkpoint)
                sync.assert_called_once_with(checkpoint.parent)

    def test_identical_prepared_checkpoint_is_consumed_and_next_publish_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            world = recorded_world()
            checkpoint = Path(directory) / "world.json"
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                export_history(world, ledger)
                publish_checkpoint(world, ledger, checkpoint)
                with patch("checkpoint_publication.Path.replace", side_effect=OSError("crash")):
                    with self.assertRaises(OSError):
                        publish_checkpoint(world, ledger, checkpoint)
                candidate = checkpoint.with_name(checkpoint.name + ".pending")
                self.assertEqual(candidate.read_bytes(), checkpoint.read_bytes())
                self.assertEqual(recover_checkpoint(ledger, checkpoint).digest(), world.digest())
                self.assertFalse(candidate.exists())
                publish_checkpoint(world, ledger, checkpoint)

    def test_missing_or_invalid_prepared_candidate_preserves_old_checkpoint(self):
        for damage in ("missing", "bytes", "valid_digest_invalid_checkpoint"):
            with self.subTest(damage=damage), tempfile.TemporaryDirectory() as directory:
                world = recorded_world()
                checkpoint = Path(directory) / "world.json"
                with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                    export_history(world, ledger)
                    publish_checkpoint(world, ledger, checkpoint)
                    before = checkpoint.read_bytes()
                    world.advance(1)
                    with patch("checkpoint_publication.Path.replace", side_effect=OSError("crash")):
                        with self.assertRaises(OSError):
                            publish_checkpoint(world, ledger, checkpoint)
                    candidate = checkpoint.with_name(checkpoint.name + ".pending")
                    if damage == "missing":
                        candidate.unlink()
                    else:
                        candidate.write_bytes(b"{}")
                        if damage == "valid_digest_invalid_checkpoint":
                            ledger.db.execute("UPDATE checkpoint_publication SET sha256=?",
                                              (hashlib.sha256(b"{}").hexdigest(),))
                            ledger.db.commit()
                    candidate_before = candidate.read_bytes() if candidate.exists() else None
                    with self.assertRaises(ValueError):
                        recover_checkpoint(ledger, checkpoint)
                    self.assertEqual(checkpoint.read_bytes(), before)
                    self.assertEqual(candidate.read_bytes() if candidate.exists() else None, candidate_before)
                    self.assertEqual(ledger.cursor(), (1, 2))
                    self.assertEqual(ledger.db.execute("SELECT status FROM checkpoint_publication").fetchone()[0], "prepared")

    def test_process_crash_rolls_back_partial_event_index_and_witnesses(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.sqlite"
            with SQLiteHistoryLedger(path) as ledger:
                append_event_with_witnesses(ledger, Event("first", 0, "First", frozenset({1})))
                before = rows(ledger)
            script = """
import os,sys
from sqlite_history import SQLiteHistoryLedger
from atomic_witness_archive import append_event_with_witnesses
from history import Event
ledger=SQLiteHistoryLedger(sys.argv[1])
ledger.db.create_function('crash',0,lambda: os._exit(73))
ledger.db.execute("CREATE TRIGGER injected BEFORE INSERT ON event_witness_memory WHEN NEW.actor=2 BEGIN SELECT crash(); END")
append_event_with_witnesses(ledger,Event('next',1,'Next',frozenset({1,2})))
"""
            process = subprocess.run([sys.executable, "-c", script, str(path)], check=False)
            self.assertEqual(process.returncode, 73)
            with SQLiteHistoryLedger(path) as ledger:
                self.assertEqual(rows(ledger), before)
                self.assertEqual(verify_witness_memory(ledger), 1)

    def test_real_process_crashes_at_publication_boundaries(self):
        for stage in ("before_intent", "after_intent", "after_rename", "before_status", "after_status"):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                database, checkpoint = Path(directory) / "history.sqlite", Path(directory) / "world.json"
                world = recorded_world()
                with SQLiteHistoryLedger(database) as ledger:
                    export_history(world, ledger)
                    publish_checkpoint(world, ledger, checkpoint)
                old = checkpoint.read_bytes()
                script = """
import os,sys
from pathlib import Path
import checkpoint_publication as cp
from sqlite_history import SQLiteHistoryLedger
from unified_persistence import load
ledger=SQLiteHistoryLedger(sys.argv[1]); path=Path(sys.argv[2]); stage=sys.argv[3]
world=load(path); world.advance(1)
ledger.db.create_function('crash',0,lambda: os._exit(73))
if stage=='before_intent':
 ledger.db.execute("CREATE TRIGGER injected BEFORE INSERT ON checkpoint_publication BEGIN SELECT crash(); END")
elif stage=='after_intent':
 Path.replace=lambda *args: os._exit(73)
elif stage=='after_rename':
 original=cp._sync_directory
 calls=0
 def sync(path):
  global calls
  calls+=1
  if calls==2: os._exit(73)
  original(path)
 cp._sync_directory=sync
elif stage=='before_status':
 ledger.db.execute("CREATE TRIGGER injected BEFORE UPDATE ON checkpoint_publication WHEN NEW.status='published' BEGIN SELECT crash(); END")
cp.publish_checkpoint(world,ledger,path)
os._exit(73)
"""
                result = subprocess.run([sys.executable, "-c", script, str(database), str(checkpoint), stage], check=False)
                self.assertEqual(result.returncode, 73)
                with SQLiteHistoryLedger(database) as ledger:
                    ledger.db.execute("DROP TRIGGER IF EXISTS injected")
                    ledger.db.commit()
                    if stage == "before_intent":
                        self.assertEqual(checkpoint.read_bytes(), old)
                        restored = recover_checkpoint(ledger, checkpoint)
                        self.assertEqual(restored.day, 0)
                        self.assertTrue(checkpoint.with_name(checkpoint.name + ".pending").exists())
                    else:
                        restored = recover_checkpoint(ledger, checkpoint)
                        self.assertEqual(restored.day, 1)
                        self.assertEqual(verify_history(restored, ledger), len(world.history.events))
                    self.assertEqual(ledger.cursor(), (1, 2))


if __name__ == "__main__":
    unittest.main()
