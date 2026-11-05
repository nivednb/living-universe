"""Non-mutating probe of kernel compatibility with SQLite-backed event mapping.

Temporarily substitutes a read-only Mapping for the in-memory event dictionary.
Restores the original object even if validation fails. This is an experiment,
not a persistent migration or a writable event store.
"""
from archived_events import ArchivedEvents
from archive_invariants import validate_archive_knowledge
from history_archive import verify_history
from invariants import validate


def probe_archived_kernel(world, ledger):
    """Validate and encode a kernel using SQLite as its event mapping.

    The authoritative world is left unchanged. The full JSON snapshot still
    materializes all historical events, so this is NOT bounded-memory saving.
    """
    verify_history(world, ledger)
    validate_archive_knowledge(world, ledger)
    original = world.history.events
    try:
        world.history.events = ArchivedEvents(ledger)
        validate(world)
        snapshot = world.snapshot()
    finally:
        world.history.events = original
    if snapshot != world.snapshot():
        raise ValueError("archive-backed snapshot differs from authoritative snapshot")
    return snapshot
