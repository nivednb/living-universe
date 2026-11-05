"""Streaming audit of epistemic invariants against archived historical events.

Runs alongside, not instead of, current authoritative kernel validation.
Uses SQLite's read-through index without building a Python event dictionary.
"""
from archived_events import ArchivedEvents
from sqlite_history import HistoryIntegrityError


def validate_archive_knowledge(world, ledger):
    events = ArchivedEvents(ledger)
    claims = world.history.claims
    knowledge = world.history.knowledge
    ids = set(world.travelers)
    for actor, references in knowledge.items():
        if actor not in ids:
            raise HistoryIntegrityError("unknown historical knowledge holder")
        for ref in references:
            if ref in claims:
                continue
            event = events[ref] if ref in events else None
            if event is None or actor not in event.witnesses:
                raise HistoryIntegrityError("invalid direct event knowledge")
    count = 0
    for event_id in events:
        event = events[event_id]
        if event.id != event_id or event.year > world.day or not event.witnesses <= ids:
            raise HistoryIntegrityError("invalid archived event")
        for actor in event.witnesses:
            if event_id not in knowledge.get(actor, ()):
                raise HistoryIntegrityError("missing witness memory")
        if event_id in claims:
            raise HistoryIntegrityError("ambiguous event and claim ID")
        count += 1
    for claim_id, claim in claims.items():
        if claim.id != claim_id or claim.event_id not in events:
            raise HistoryIntegrityError("invalid claim event reference")
    for claim_id, claim in world.state.knowledge.items():
        if claim.id != claim_id or claim.origin_event_id not in events:
            raise HistoryIntegrityError("invalid world claim provenance")
        if any(ref not in claims and ref not in world.state.knowledge
               and ref not in events for ref in claim.evidence_ids):
            raise HistoryIntegrityError("invalid world claim evidence")
    return count
