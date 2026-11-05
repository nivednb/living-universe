"""Read-only SQLite history mapping for inspection without materializing all events.

Unlike the in-memory HistoricalLedger, this is an archive reader, not a
drop-in mutable kernel history. Kernel checkpoint and epistemic invariants
still require a separate migration before the live dictionary can be removed.
"""
from collections.abc import Mapping
from history import Event
from sqlite_history import HistoryIntegrityError


class ArchivedEvents(Mapping):
    """Read-through event mapping, with no persistent Python event cache."""

    def __init__(self, ledger):
        self.ledger = ledger

    def __len__(self):
        return self.ledger.cursor()[1]

    def __iter__(self):
        for _, _, kind, _, payload in self.ledger.iter_events():
            if kind != "historical_event":
                raise HistoryIntegrityError("unexpected archive event kind")
            yield payload["id"]

    def __getitem__(self, event_id):
        # Current archive schema indexes sequence rather than event ID. An
        # explicit scan is correct but potentially slow: add an indexed ID
        # column before using this mapping for high-volume provenance lookups.
        for _, day, kind, actor, payload in self.ledger.iter_events():
            if kind != "historical_event" or actor is not None:
                raise HistoryIntegrityError("unexpected archive record")
            if payload["id"] == event_id:
                return Event(event_id, day, payload["description"],
                             frozenset(payload["witnesses"]))
        raise KeyError(event_id)
