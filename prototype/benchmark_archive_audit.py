"""Audit allocation probe, not a bounded-memory or capacity guarantee.

Run from prototype/: python benchmark_archive_audit.py
tracemalloc observes additional Python allocations only, not SQLite/native RSS.
"""
import gc
import json
import platform
from pathlib import Path
import sqlite3
import tempfile
from time import perf_counter
import tracemalloc

from atomic_witness_archive import verify_witness_memory
from benchmark_unified import build
from history import Event
from sqlite_history import SQLiteHistoryLedger


def measure(operation):
    gc.collect()
    tracemalloc.start()
    start = perf_counter()
    result = operation()
    elapsed = perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del result
    return {"seconds": round(elapsed, 6), "additional_python_peak_bytes": peak}


def run(count):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "history.sqlite"
        with SQLiteHistoryLedger(path) as ledger:
            records = ((i, i // 100, "historical_event", None,
                        {"id": f"event-{i}", "description": "fixed-size observation", "witnesses": []})
                       for i in range(count))
            append = measure(lambda: ledger.append_many(records, witness_rows=[]))
            scan = measure(lambda: sum(1 for _ in ledger.iter_events()))
            index = measure(ledger.check_event_id_index)
            witnesses = measure(lambda: verify_witness_memory(ledger))
            first_lookup = measure(lambda: ledger.get_event_by_id(f"event-{count - 1}"))
            warm_lookups = measure(lambda: sum(ledger.get_event_by_id(f"event-{i % count}") is not None
                                             for i in range(1000)))
            database_files = {p.name: p.stat().st_size for p in Path(directory).iterdir()}
        # The live kernel still owns all events and witness knowledge in memory.
        # Measure snapshot allocation *in addition* to that already allocated state.
        world = build(1)
        for i in range(count):
            world.history.record(Event(f"event-{i}", 0, "fixed-size observation", frozenset({0})))
        snapshot = measure(world.snapshot)
    return {"events": count, "append_single_batch": append, "stream_scan": scan,
            "id_index_audit": index, "witness_audit": witnesses,
            "first_id_lookup": first_lookup, "warm_1000_id_lookups": warm_lookups,
            "full_live_snapshot": snapshot, "sqlite_files_bytes": database_files}


if __name__ == "__main__":
    print(json.dumps({"python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
                      "platform": platform.platform(), "observations": [run(n) for n in (1000, 10000)]},
                     indent=2, sort_keys=True))
