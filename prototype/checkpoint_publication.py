"""Crash-recoverable checkpoint publication for an already verified SQLite mirror.

Protocol (single writer): write and fsync immutable candidate JSON; commit a
SQLite publication intent containing its SHA-256; atomically replace the public
checkpoint; fsync directory; mark intent published. On restart, an unfinished
intent may be completed only from the digest-matching candidate or checkpoint.
This does NOT coordinate simulation event appends; the archive must already
match the candidate checkpoint exactly before publication.
"""
import hashlib
import json
import os
from pathlib import Path

from history_archive import verify_history
from sqlite_history import HistoryIntegrityError
from unified_persistence import encode, load


def _digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _sync_directory(directory):
    if os.name == "posix":
        fd = os.open(str(directory), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _init(ledger):
    ledger.db.execute("""CREATE TABLE IF NOT EXISTS checkpoint_publication (
        id INTEGER PRIMARY KEY CHECK(id=1),
        destination TEXT NOT NULL,
        candidate TEXT NOT NULL,
        sha256 TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('prepared','published'))
    )""")


def publish_checkpoint(world, ledger, path):
    """Publish only a checkpoint whose history equals the committed archive."""
    verify_history(world, ledger)
    destination = Path(path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    _init(ledger)
    if ledger.db.execute("SELECT 1 FROM checkpoint_publication WHERE id=1 AND status='prepared'").fetchone():
        raise HistoryIntegrityError("unfinished checkpoint publication; recover first")
    state = encode(world)
    candidate = destination.with_name(destination.name + ".pending")
    if candidate.exists():
        raise HistoryIntegrityError("unrecognized pending checkpoint exists")
    with candidate.open("x", encoding="utf-8") as stream:
        json.dump(state, stream, sort_keys=True, separators=(",", ":"), allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    _sync_directory(destination.parent)
    digest = _digest(candidate)
    with ledger.db:
        ledger.db.execute("""INSERT INTO checkpoint_publication
            (id,destination,candidate,sha256,status) VALUES(1,?,?,?,'prepared')
            ON CONFLICT(id) DO UPDATE SET destination=excluded.destination,
            candidate=excluded.candidate,sha256=excluded.sha256,status='prepared'""",
            (str(destination), str(candidate), digest))
    candidate.replace(destination)
    _sync_directory(destination.parent)
    with ledger.db:
        ledger.db.execute("UPDATE checkpoint_publication SET status='published' WHERE id=1")
    return digest


def recover_checkpoint(ledger, path):
    """Finish an interrupted publication without guessing or losing history."""
    destination = Path(path).resolve()
    _init(ledger)
    row = ledger.db.execute(
        "SELECT destination,candidate,sha256,status FROM checkpoint_publication WHERE id=1"
    ).fetchone()
    if row is None:
        raise HistoryIntegrityError("no checkpoint publication record")
    stored_destination, candidate_name, digest, status = row
    if stored_destination != str(destination):
        raise HistoryIntegrityError("checkpoint destination mismatch")
    candidate = Path(candidate_name)
    if status == "prepared":
        if destination.exists() and _digest(destination) == digest:
            pass
        elif candidate.exists() and _digest(candidate) == digest:
            candidate.replace(destination)
            _sync_directory(destination.parent)
        else:
            raise HistoryIntegrityError("checkpoint candidate missing or modified")
    if not destination.exists() or _digest(destination) != digest:
        raise HistoryIntegrityError("published checkpoint digest mismatch")
    world = load(destination)
    verify_history(world, ledger)
    if status == "prepared":
        with ledger.db:
            ledger.db.execute("UPDATE checkpoint_publication SET status='published' WHERE id=1")
    return world
