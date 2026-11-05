"""Atomic SQLite event + witness-memory append, opt-in migration prototype.

This keeps witness rows and their event in one SQLite transaction. It does not
make the external JSON checkpoint atomic, or migrate communicated claims.
"""
from history import Event
from sqlite_history import HistoryIntegrityError


def append_event_with_witnesses(ledger, event):
    if not isinstance(event, Event) or not isinstance(event.id, str) or not event.id:
        raise ValueError("invalid historical event")
    if type(event.year) is not int or event.year < 0:
        raise ValueError("invalid live event day")
    if not isinstance(event.description, str):
        raise ValueError("invalid description")
    if any(type(actor) is not int or actor < 0 or actor >= 2**63
           for actor in event.witnesses):
        raise ValueError("invalid witness ID")
    last, count = ledger.cursor()
    if last is not None and last != count - 1:
        raise HistoryIntegrityError("noncontiguous event sequence")
    ledger.append_many(
        [(count, event.year, "historical_event", None,
          {"id": event.id, "year": event.year,
           "description": event.description,
           "witnesses": sorted(event.witnesses)})],
        witness_rows=[(event.id, actor) for actor in sorted(event.witnesses)],
    )
    return count


def verify_witness_memory(ledger):
    """Stream and compare persisted witness rows to canonical event payloads."""
    db = ledger.db
    table = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='event_witness_memory'").fetchone()
    if table is None:
        if ledger.cursor()[1] == 0:
            return 0
        raise HistoryIntegrityError("witness-memory table missing")
    cursor = db.execute(
        "SELECT w.event_id,w.actor FROM event_witness_memory w "
        "JOIN event_ids i ON i.event_id=w.event_id ORDER BY i.sequence,w.actor"
    )
    count = 0
    for _, _, kind, _, payload in ledger.iter_events():
        if kind != "historical_event":
            continue
        event_id = payload["id"]
        for actor in sorted(payload["witnesses"]):
            actual = cursor.fetchone()
            if actual != (event_id, actor):
                raise HistoryIntegrityError("witness-memory mismatch")
            count += 1
    if cursor.fetchone() is not None:
        raise HistoryIntegrityError("extra witness-memory row")
    return count
