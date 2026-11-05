"""Opt-in append-only event writer; not yet attached to the live kernel.

Only the historical event and its ID index are committed atomically. Witness
knowledge, claims, and JSON checkpoints are NOT included in that transaction.
"""
from archived_events import ArchivedEvents
from history import Event
from sqlite_history import HistoryIntegrityError


class ArchivedEventWriter:
    def __init__(self, ledger):
        self.ledger = ledger
        self.events = ArchivedEvents(ledger)

    def record(self, event):
        if not isinstance(event, Event):
            raise TypeError("expected Event")
        if not isinstance(event.id, str) or not event.id:
            raise ValueError("invalid event ID")
        if type(event.year) is not int or event.year < 0:
            raise ValueError("live archive writer requires nonnegative simulation day")
        if any(type(actor) is not int or actor < 0 for actor in event.witnesses):
            raise ValueError("invalid witness ID")
        last, count = self.ledger.cursor()
        if last is not None and last != count - 1:
            raise HistoryIntegrityError("noncontiguous archive sequence")
        self.ledger.append_many([(
            count, event.year, "historical_event", None,
            {"id": event.id, "year": event.year,
             "description": event.description, "witnesses": sorted(event.witnesses)}
        )])
        return event.id

    def record_kernel(self, day, kind, actor, detail, witnesses=()):
        """Allocate the next deterministic ID without an in-memory event map."""
        if type(day) is not int or day < 0:
            raise ValueError("invalid simulation day")
        if type(actor) is not int or actor < 0:
            raise ValueError("invalid actor")
        last, count = self.ledger.cursor()
        if last is not None and last != count - 1:
            raise HistoryIntegrityError("noncontiguous archive sequence")
        event = Event(f"kernel-{count}", day, f"{kind}: {detail}",
                      frozenset(witnesses))
        self.record(event)
        return event
