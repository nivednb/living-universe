"""Lossless export and verification bridge for existing unified-kernel history.

This deliberately does not remove in-memory events or change checkpoint format.
It establishes a safe compatibility baseline before a bounded-memory migration.
"""
from history import Event
from sqlite_history import HistoryIntegrityError


def export_history(world, ledger):
    """Append the complete history of a fresh world to an empty SQLite ledger.

    Refuses nonempty destinations: silently reconciling independent checkpoint
    and SQLite commits could otherwise lose or duplicate authoritative history.
    """
    if ledger.cursor() != (None, 0):
        raise HistoryIntegrityError("export requires an empty history ledger")
    records = (
        (index, max(0, event.year), "historical_event", None,
         {"id": event.id, "year": event.year, "description": event.description,
          "witnesses": sorted(event.witnesses)})
        for index, event in enumerate(world.history.events.values())
    )
    count = 0
    batch = []
    for record in records:
        batch.append(record)
        if len(batch) == 256:
            count += ledger.append_many(batch, witness_rows=_witness_rows(batch))
            batch.clear()
    if batch:
        count += ledger.append_many(batch, witness_rows=_witness_rows(batch))
    return count


def verify_history(world, ledger):
    """Check all exported events exactly, including order and witness identity."""
    from atomic_witness_archive import verify_witness_memory
    # Nonempty pre-witness archives remain readable through ArchivedEvents, but
    # are not complete mirrors suitable for checkpoint publication or recovery.
    verify_witness_memory(ledger)
    expected = iter(world.history.events.values())
    count = 0
    for sequence, day, kind, actor, payload in ledger.iter_events():
        event = next(expected, None)
        if (event is None or sequence != count or day != max(0, event.year) or
                kind != "historical_event" or actor is not None or
                payload != {"id": event.id, "year": event.year, "description": event.description,
                            "witnesses": sorted(event.witnesses)}):
            raise HistoryIntegrityError(f"history mismatch at index {count}")
        count += 1
    if next(expected, None) is not None:
        raise HistoryIntegrityError("archive is missing events")
    return count


def _witness_rows(batch):
    return [(record[4]["id"], actor) for record in batch for actor in record[4]["witnesses"]]
