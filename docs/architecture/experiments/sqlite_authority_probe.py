"""Isolated design evidence, NOT a kernel persistence adapter or migration.

Stores a complete, growing JSON snapshot on every test commit deliberately.
This is a small atomicity oracle, not the proposed normalized production schema.
All databases are temporary. Run directly with Python 3.12 or 3.13.
"""
import hashlib
import io
import json
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import tempfile
from time import perf_counter
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "prototype"))
from benchmark_unified import build, schedule
from history import Claim, Event
from unified_persistence import decode, encode
from world_state import KnowledgeClaim


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def connect(path):
    db = sqlite3.connect(path, isolation_level=None)
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS metadata (
            id INTEGER PRIMARY KEY CHECK(id=1), universe TEXT NOT NULL,
            head INTEGER NOT NULL, parent_head INTEGER);
        CREATE TABLE IF NOT EXISTS commits (
            number INTEGER PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
            request_hash TEXT NOT NULL, body BLOB NOT NULL, digest TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS history_events (
            ordinal INTEGER PRIMARY KEY, id TEXT NOT NULL UNIQUE,
            year TEXT NOT NULL, description TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS witnesses (
            event_id TEXT NOT NULL REFERENCES history_events(id), actor TEXT NOT NULL,
            PRIMARY KEY(event_id,actor));
        CREATE TABLE IF NOT EXISTS known_refs (
            actor TEXT NOT NULL, reference TEXT NOT NULL, PRIMARY KEY(actor,reference));
    """)
    return db


def seed_world():
    world = build(2, 42)
    world.history.record(Event("ancient", -100, "Synthetic past", frozenset({0})))
    world.history.publish_claim(Claim("rumor", "ancient", "An uncertain story", "archive"))
    world.history.communicate("rumor", 1)
    world.state.add_claim(KnowledgeClaim("belief", "Possibly", "ancient", ("rumor",)))
    world.state.learn(1, "belief")
    schedule(world, 0)
    world.validate()
    return encode(world)


def commit(db, state, request_id, request_hash, expected_head, fault=None):
    """Test-only complete snapshot commit; never invokes a kernel command."""
    decode(state)  # Prototype invariants, not a substitute for DB constraints.
    body = canonical(state)
    db.execute("BEGIN IMMEDIATE")
    try:
        receipt = db.execute("SELECT number,request_hash FROM commits WHERE request_id=?", (request_id,)).fetchone()
        if receipt:
            if receipt[1] != request_hash:
                raise ValueError("request key reused for different input")
            db.execute("ROLLBACK")
            return receipt[0]
        row = db.execute("SELECT head FROM metadata WHERE id=1").fetchone()
        if (row[0] if row else None) != expected_head:
            raise ValueError("stale parent")
        number = 0 if expected_head is None else expected_head + 1
        db.execute("INSERT INTO commits VALUES(?,?,?,?,?)",
                   (number, request_id, request_hash, body, hashlib.sha256(body).hexdigest()))
        db.execute("INSERT INTO metadata VALUES(1,'canonical',?,NULL) "
                   "ON CONFLICT(id) DO UPDATE SET head=excluded.head", (number,))
        if fault == "after_state":
            os_exit()
        previous = list(db.execute("SELECT id,year,description FROM history_events ORDER BY ordinal"))
        if previous != [(e[0], str(e[1]), e[2]) for e in state["events"][:len(previous)]]:
            raise ValueError("history prefix changed")
        for ordinal in range(len(previous), len(state["events"])):
            eid, year, description, witnesses = state["events"][ordinal]
            db.execute("INSERT INTO history_events VALUES(?,?,?,?)", (ordinal, eid, str(year), description))
            db.executemany("INSERT INTO witnesses VALUES(?,?)", [(eid, str(a)) for a in witnesses])
        db.execute("DELETE FROM known_refs")
        db.executemany("INSERT INTO known_refs VALUES(?,?)",
                       [(actor, ref) for actor, refs in state["history_knowledge"].items() for ref in refs])
        if fault == "foreign_key":
            db.execute("INSERT INTO witnesses VALUES('missing','0')")
        audit_current(db)  # Intentionally a full scan in this tiny correctness oracle.
        if fault == "before_commit":
            os_exit()
        db.execute("COMMIT")
        if fault == "after_commit":
            os_exit()
        return number
    except BaseException:
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise


def os_exit():
    import os
    os._exit(73)


def read(db, at=None):
    if at is None:
        at = db.execute("SELECT head FROM metadata WHERE id=1").fetchone()[0]
    row = db.execute("SELECT body,digest FROM commits WHERE number=?", (at,)).fetchone()
    if row is None or hashlib.sha256(row[0]).hexdigest() != row[1]:
        raise ValueError("missing or damaged committed state")
    state = json.loads(row[0])
    decode(state)
    return state


def audit_current(db):
    state = read(db)
    events = [(e[0], str(e[1]), e[2]) for e in state["events"]]
    if list(db.execute("SELECT id,year,description FROM history_events ORDER BY ordinal")) != events:
        raise ValueError("history mismatch")
    expected = {(e[0], str(a)) for e in state["events"] for a in e[3]}
    if set(db.execute("SELECT event_id,actor FROM witnesses")) != expected:
        raise ValueError("witness mismatch")
    expected = {(a, ref) for a, refs in state["history_knowledge"].items() for ref in refs}
    if set(db.execute("SELECT actor,reference FROM known_refs")) != expected:
        raise ValueError("memory mismatch")
    if db.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("foreign key mismatch")
    return state


class AuthorityProbe(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "authority.sqlite"
        self.db = connect(self.path)
        self.addCleanup(self.db.close)
        self.before = seed_world()
        commit(self.db, self.before, "genesis", "genesis", None)
        world = decode(self.before)
        world.advance(5)
        self.after = encode(world)

    def test_atomic_fk_failure_restores_state_history_rng_pending_and_memories(self):
        with self.assertRaises(sqlite3.IntegrityError):
            commit(self.db, self.after, "advance", "advance:5", 0, "foreign_key")
        self.assertEqual(audit_current(self.db), self.before)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM commits").fetchone()[0], 1)

    def test_real_process_exits_before_and_after_commit(self):
        for fault in ("after_state", "before_commit", "after_commit"):
            with self.subTest(fault=fault):
                path = Path(self.directory.name) / (fault + ".sqlite")
                db = connect(path)
                commit(db, self.before, "genesis", "genesis", None)
                db.close()
                candidate = Path(self.directory.name) / (fault + ".json")
                candidate.write_bytes(canonical(self.after))
                result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker",
                                         str(path), str(candidate), fault], check=False)
                self.assertEqual(result.returncode, 73)
                db = connect(path)
                try:
                    expected = self.after if fault == "after_commit" else self.before
                    self.assertEqual(audit_current(db), expected)
                    if fault == "after_commit":
                        # Lost acknowledgement: duplicate receipt resolves the outcome.
                        self.assertEqual(commit(db, self.after, "advance", "advance:5", 0), 1)
                        self.assertEqual(audit_current(db), self.after)
                finally:
                    db.close()

    def test_idempotency_and_stale_parent(self):
        self.assertEqual(commit(self.db, self.after, "advance", "advance:5", 0), 1)
        self.assertEqual(commit(self.db, self.before, "advance", "advance:5", 0), 1)
        with self.assertRaises(ValueError):
            commit(self.db, self.after, "advance", "different-command", 0)
        with self.assertRaises(ValueError):
            commit(self.db, self.after, "other", "advance:5", 0)
        self.assertEqual(audit_current(self.db), self.after)

    def test_reader_snapshot_isolation_and_read_only_connection(self):
        reader = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, isolation_level=None)
        try:
            reader.execute("BEGIN")
            self.assertEqual(read(reader), self.before)
            commit(self.db, self.after, "advance", "advance:5", 0)
            self.assertEqual(read(reader), self.before)
            with self.assertRaises(sqlite3.OperationalError):
                reader.execute("UPDATE metadata SET head=0")
            reader.execute("ROLLBACK")
            self.assertEqual(read(reader), self.after)
        finally:
            reader.close()

    def test_backup_fork_changes_only_child(self):
        child_path = Path(self.directory.name) / "experiment.sqlite"
        child = sqlite3.connect(child_path, isolation_level=None)
        self.db.backup(child)
        child.execute("PRAGMA foreign_keys=ON")
        child.execute("PRAGMA synchronous=FULL")
        try:
            child.execute("UPDATE metadata SET universe='experiment',parent_head=0")
            self.assertEqual(audit_current(child), self.before)
            commit(child, self.after, "experiment-advance", "advance:5", 0)
            self.assertEqual(audit_current(child), self.after)
            self.assertEqual(audit_current(self.db), self.before)
        finally:
            child.close()

    def test_corruption_is_detected_without_repair(self):
        self.db.execute("UPDATE commits SET body=? WHERE number=0", (b"{}",))
        with self.assertRaises(ValueError):
            read(self.db)
        self.assertEqual(self.db.execute("SELECT body FROM commits WHERE number=0").fetchone()[0], b"{}")

    def test_missing_memory_is_detected_without_repair(self):
        self.db.execute("DELETE FROM witnesses")
        with self.assertRaises(ValueError):
            audit_current(self.db)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM witnesses").fetchone()[0], 0)

    def test_committed_cut_restore_preserves_signed_year_and_continuation(self):
        commit(self.db, self.after, "advance", "advance:5", 0)
        self.assertEqual(read(self.db, at=0), self.before)
        self.assertEqual(read(self.db)["events"][0][1], -100)
        a, b = decode(read(self.db)), decode(self.after)
        a.advance(10)
        b.advance(10)
        self.assertEqual(a.digest(), b.digest())


def compression_observation(population):
    world = build(population)
    for iteration in range(5):
        schedule(world, iteration)
        world.advance(10)
    start = perf_counter()
    body = canonical(encode(world))
    encode_seconds = perf_counter() - start
    start = perf_counter()
    packed = zlib.compress(body, level=6)
    compress_seconds = perf_counter() - start
    start = perf_counter()
    unpacked = zlib.decompress(packed)
    decompress_seconds = perf_counter() - start
    if unpacked != body or decode(json.loads(unpacked)).digest() != world.digest():
        raise AssertionError("compression changed canonical state")
    return {"agents": population, "days": world.day, "history_events": len(world.history.events),
            "raw_bytes": len(body), "zlib6_bytes": len(packed), "encode_seconds": round(encode_seconds, 6),
            "compress_seconds": round(compress_seconds, 6), "decompress_seconds": round(decompress_seconds, 6),
            "lossless_roundtrip": True}


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        db = connect(Path(sys.argv[2]))
        commit(db, json.loads(Path(sys.argv[3]).read_bytes()), "advance", "advance:5", 0, sys.argv[4])
        return 1
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AuthorityProbe)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    if not result.wasSuccessful():
        print(output.getvalue(), file=sys.stderr)
        return 1
    print(json.dumps({"status": "isolated design probe; not production persistence", "python": platform.python_version(),
                      "sqlite": sqlite3.sqlite_version, "zlib": zlib.ZLIB_RUNTIME_VERSION,
                      "platform": platform.platform(),
                      "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                      "compression": [compression_observation(n) for n in (100, 1000)],
                      "not_proven": ["production row-delta capture", "complete causal replay", "power-loss durability",
                                     "large-population throughput", "bounded process memory", "production migration"]},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
