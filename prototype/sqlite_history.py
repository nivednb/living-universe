"""Optional lossless, disk-backed historical event ledger.

Independent of the existing in-memory HistoricalLedger and JSON checkpoints.
This module does not claim atomicity across an external checkpoint file.
"""
import hashlib
import json
import sqlite3
from pathlib import Path


class HistoryIntegrityError(ValueError):
    """Stored events do not satisfy the canonical ledger contract."""


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


class SQLiteHistoryLedger:
    """Single-writer append-only history with streaming reads.

    Event sequence is a caller-supplied monotonically increasing integer. A
    duplicate is rejected even if its contents match; callers must reconcile
    checkpoint cursors before resuming writes.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path))
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                sequence INTEGER PRIMARY KEY,
                day INTEGER NOT NULL CHECK(day >= 0),
                kind TEXT NOT NULL CHECK(length(kind) > 0),
                actor INTEGER,
                payload TEXT NOT NULL,
                digest TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS events_by_day ON events(day, sequence);
            CREATE INDEX IF NOT EXISTS events_by_actor ON events(actor, sequence);
            CREATE TABLE IF NOT EXISTS event_ids (
                event_id TEXT PRIMARY KEY,
                sequence INTEGER NOT NULL UNIQUE REFERENCES events(sequence)
            );
        """)
        self._index_verified = False

    def rebuild_event_id_index(self, batch_size=256):
        """Rebuild ID mappings with bounded Python memory and atomic rollback.

        Every source event is digest-verified while streaming. Duplicate IDs
        fail the SQLite PRIMARY KEY constraint and roll back the entire rebuild.
        This is an explicit migration, never an automatic repair.
        """
        if type(batch_size) is not int or batch_size < 1:
            raise ValueError("batch_size must be positive")
        self._index_verified = False
        count = 0
        with self.db:
            self.db.execute("DELETE FROM event_ids")
            batch = []
            for sequence, _, kind, _, payload in self.iter_events(batch_size=batch_size):
                if kind != "historical_event":
                    continue
                event_id = payload.get("id") if isinstance(payload, dict) else None
                if not isinstance(event_id, str) or not event_id:
                    raise HistoryIntegrityError("invalid historical event ID")
                batch.append((event_id, sequence))
                if len(batch) == batch_size:
                    self.db.executemany(
                        "INSERT INTO event_ids(event_id,sequence) VALUES(?,?)", batch
                    )
                    count += len(batch)
                    batch.clear()
            if batch:
                self.db.executemany(
                    "INSERT INTO event_ids(event_id,sequence) VALUES(?,?)", batch
                )
                count += len(batch)
            # Audit before committing, so any mismatch rolls back the rebuild.
            if self.check_event_id_index() != count:
                raise HistoryIntegrityError("historical ID index count mismatch")
        self._index_verified = True
        return count

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def append_many(self, records):
        """Commit a batch atomically; fail the whole batch on invalid input."""
        prepared = []
        for sequence, day, kind, actor, payload in records:
            if type(sequence) is not int or sequence < 0 or sequence > 2**63 - 1:
                raise ValueError("sequence must be a nonnegative SQLite integer")
            if type(day) is not int or day < 0 or day > 2**63 - 1:
                raise ValueError("day must be a nonnegative SQLite integer")
            if not isinstance(kind, str) or not kind:
                raise ValueError("kind must be a nonempty string")
            if actor is not None and (type(actor) is not int or not (-2**63 <= actor < 2**63)):
                raise ValueError("actor must be a SQLite integer or None")
            body = _canonical(payload)
            digest = hashlib.sha256(_canonical([sequence, day, kind, actor, payload]).encode("utf-8")).hexdigest()
            prepared.append((sequence, day, kind, actor, body, digest))
        if not prepared:
            return 0
        event_ids = []
        for row in prepared:
            if row[2] == "historical_event":
                payload = json.loads(row[4])
                event_id = payload.get("id") if isinstance(payload, dict) else None
                if not isinstance(event_id, str) or not event_id:
                    raise ValueError("historical event must have a nonempty string id")
                event_ids.append((event_id, row[0]))
        if any(a[0] >= b[0] for a, b in zip(prepared, prepared[1:])):
            raise ValueError("batch sequences must strictly increase")
        last = self.db.execute("SELECT MAX(sequence), MAX(day) FROM events").fetchone()
        if last[0] is not None and prepared[0][0] <= last[0]:
            raise HistoryIntegrityError("sequence must exceed committed cursor")
        # Day monotonicity is checked against the last appended event, not MAX(day).
        latest = self.db.execute("SELECT day FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
        if latest and prepared[0][1] < latest[0]:
            raise ValueError("day must not go backwards")
        if any(a[1] > b[1] for a, b in zip(prepared, prepared[1:])):
            raise ValueError("batch days must not go backwards")
        with self.db:
            self.db.executemany(
                "INSERT INTO events(sequence,day,kind,actor,payload,digest) VALUES(?,?,?,?,?,?)",
                prepared,
            )
            self.db.executemany("INSERT INTO event_ids(event_id,sequence) VALUES(?,?)", event_ids)
        return len(prepared)

    def iter_events(self, *, from_sequence=0, to_sequence=None, actor=None,
                    start_day=None, end_day=None, batch_size=256):
        if type(batch_size) is not int or batch_size < 1:
            raise ValueError("batch_size must be positive")
        sql = "SELECT sequence,day,kind,actor,payload,digest FROM events WHERE sequence >= ?"
        params = [from_sequence]
        for column, value, op in (("sequence", to_sequence, "<="), ("actor", actor, "="),
                                  ("day", start_day, ">="), ("day", end_day, "<=")):
            if value is not None:
                sql += f" AND {column} {op} ?"
                params.append(value)
        cursor = self.db.execute(sql + " ORDER BY sequence", params)
        while rows := cursor.fetchmany(batch_size):
            for sequence, day, kind, event_actor, body, digest in rows:
                payload = json.loads(body)
                expected = hashlib.sha256(
                    _canonical([sequence, day, kind, event_actor, payload]).encode("utf-8")
                ).hexdigest()
                if digest != expected or body != _canonical(payload):
                    raise HistoryIntegrityError(f"corrupt event at sequence {sequence}")
                yield sequence, day, kind, event_actor, payload

    def check_event_id_index(self):
        """Verify every indexed ID against its canonical, digest-checked event.

        This is an explicit full scan with constant auxiliary Python memory;
        SQLite enforces unique IDs and sequences. The first ID lookup performs
        this scan once per session.
        """
        index = self.db.execute(
            "SELECT event_id,sequence FROM event_ids ORDER BY sequence"
        )
        count = 0
        for sequence, _, kind, _, payload in self.iter_events():
            if kind != "historical_event":
                continue
            event_id = payload.get("id") if isinstance(payload, dict) else None
            if not isinstance(event_id, str) or not event_id:
                raise HistoryIntegrityError("invalid historical event ID")
            actual = index.fetchone()
            if actual != (event_id, sequence):
                raise HistoryIntegrityError("historical ID index mismatch; rebuild required")
            count += 1
        if index.fetchone() is not None:
            raise HistoryIntegrityError("historical ID index has extra entries")
        return count

    def get_event_by_id(self, event_id):
        """Indexed historical event lookup, returning verified canonical record."""
        if not isinstance(event_id, str):
            raise TypeError("event_id must be a string")
        if not self._index_verified:
            self.check_event_id_index()
            self._index_verified = True
        row = self.db.execute("SELECT sequence FROM event_ids WHERE event_id=?", (event_id,)).fetchone()
        if row is None:
            return None
        records = self.iter_events(from_sequence=row[0], to_sequence=row[0])
        record = next(records, None)
        if record is None or record[2] != "historical_event" or record[4].get("id") != event_id:
            raise HistoryIntegrityError("historical event ID index mismatch")
        return record

    def cursor(self):
        row = self.db.execute("SELECT MAX(sequence), COUNT(*) FROM events").fetchone()
        return row[0], row[1]
