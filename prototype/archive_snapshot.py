"""Verified read-only historical snapshot from SQLite.

This is a transition seam, NOT a checkpoint format or a mutable kernel store.
The live kernel remains authoritative until cross-store crash recovery exists.
"""
from archived_events import ArchivedEvents
from history_archive import verify_history
from sqlite_history import HistoryIntegrityError


def snapshot_with_archive(world, ledger):
    """Return the canonical kernel snapshot after verifying its SQLite mirror.

    This proves the external archive can reproduce the historical event section
    without altering the kernel, its digest, or its existing checkpoint contract.
    Memory remains O(number of events) because the JSON snapshot is materialized.
    """
    verify_history(world, ledger)
    snapshot = world.snapshot()
    archived = ArchivedEvents(ledger)
    events = [
        [event.id, event.year, event.description, sorted(event.witnesses)]
        for event in archived.values()
    ]
    if events != snapshot["events"]:
        raise HistoryIntegrityError("archive differs from authoritative snapshot")
    snapshot["events"] = events
    return snapshot
