"""Fail-closed recovery checks for JSON checkpoint + SQLite mirror.

The checkpoint remains authoritative. This module deliberately does not
truncate, replay, or modify either store on mismatch.
"""
from history_archive import verify_history
from sqlite_history import HistoryIntegrityError
from unified_persistence import load


def load_verified_checkpoint(checkpoint_path, ledger, *, audit_knowledge=False):
    """Load a checkpoint only when its full historical mirror matches.

    An archive ahead of the checkpoint (e.g. crash after SQLite commit) is
    rejected, not silently accepted. Recovery requires an explicit policy.
    """
    world = load(checkpoint_path)
    verify_history(world, ledger)
    if audit_knowledge:
        from archive_invariants import validate_archive_knowledge
        validate_archive_knowledge(world, ledger)
    return world


def check_checkpoint_cursor(checkpoint_path, ledger, *, audit_knowledge=False):
    """Verify full archive and return its last sequence and count."""
    world = load_verified_checkpoint(checkpoint_path, ledger, audit_knowledge=audit_knowledge)
    last, count = ledger.cursor()
    if count != len(world.history.events) or last != (count - 1 if count else None):
        raise HistoryIntegrityError("checkpoint/archive cursor mismatch")
    return last, count
