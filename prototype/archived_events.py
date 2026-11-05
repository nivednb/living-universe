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
        record = self.ledger.get_event_by_id(event_id)
        if record is None:
            raise KeyError(event_id)
        _, day, kind, actor, payload = record
        if kind != "historical_event" or actor is not None:
            raise HistoryIntegrityError("unexpected archive record")
        return Event(event_id, payload.get("year", day), payload["description"],
                     frozenset(payload["witnesses"]))
