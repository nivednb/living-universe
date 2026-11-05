"""Opt-in append-only event writer; not yet attached to the live kernel.

Events, their ID index and witness rows commit atomically. Communicated claims,
in-memory knowledge and JSON checkpoints are NOT included in that transaction.
"""
from archived_events import ArchivedEvents
from history import Event
from sqlite_history import HistoryIntegrityError


class ArchivedEventWriter:
    def __init__(self, ledger, reserved_claim_ids=()):
        self.ledger = ledger
        self.reserved_claim_ids = frozenset(reserved_claim_ids)
        self.events = ArchivedEvents(ledger)

    def record(self, event):
        if not isinstance(event, Event):
            raise TypeError("expected Event")
        if not isinstance(event.id, str) or not event.id:
            raise ValueError("invalid event ID")
        if event.id in self.reserved_claim_ids:
            raise ValueError("event ID conflicts with an existing claim")
        if not isinstance(event.description, str):
            raise ValueError("invalid event description")
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
        )], witness_rows=[(event.id, actor) for actor in sorted(event.witnesses)])
        return event.id

    def record_kernel(self, day, kind, actor, detail, witnesses=None):
        """Allocate the next deterministic ID without an in-memory event map."""
        if type(day) is not int or day < 0:
            raise ValueError("invalid simulation day")
        if type(actor) is not int or actor < 0:
            raise ValueError("invalid actor")
        if not isinstance(kind, str) or not kind or not isinstance(detail, str):
            raise ValueError("invalid event kind or detail")
        if witnesses is None:
            witnesses = (actor,)
        witnesses = tuple(witnesses)
        if any(type(witness) is not int or witness < 0 for witness in witnesses):
            raise ValueError("invalid witness")
        last, count = self.ledger.cursor()
        if last is not None and last != count - 1:
            raise HistoryIntegrityError("noncontiguous archive sequence")
        index = count
        while f"kernel-{index}" in self.reserved_claim_ids or f"kernel-{index}" in self.events:
            index += 1
        event = Event(f"kernel-{index}", day, f"{kind}: {detail}",
                      frozenset(witnesses))
        self.record(event)
        return event
