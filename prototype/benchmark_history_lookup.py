"""Reproducible indexed versus streaming historical lookup benchmark.

Run from prototype/: python benchmark_history_lookup.py --events 100000 --lookups 1000
Results are local measurements, not CI performance guarantees.
"""
import argparse
import random
import tempfile
import time
from pathlib import Path

from sqlite_history import SQLiteHistoryLedger


def run(events, lookups):
    rng = random.Random(42)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "history.sqlite"
        with SQLiteHistoryLedger(path) as ledger:
            for start in range(0, events, 1000):
                ledger.append_many(
                    (i, i // 100, "historical_event", None,
                     {"id": f"event-{i}", "description": f"Event {i}", "witnesses": []})
                    for i in range(start, min(start + 1000, events))
                )
            targets = [f"event-{rng.randrange(events)}" for _ in range(lookups)]
            t0 = time.perf_counter()
            for event_id in targets:
                assert ledger.get_event_by_id(event_id)[4]["id"] == event_id
            indexed = time.perf_counter() - t0
            # A deliberately small linear baseline, because N*lookups scans
            # become prohibitively expensive at the largest archive sizes.
            sample = targets[:min(10, lookups)]
            t1 = time.perf_counter()
            for event_id in sample:
                match = next((row for row in ledger.iter_events() if row[4]["id"] == event_id), None)
                assert match is not None
            linear = time.perf_counter() - t1
            return {"events": events, "indexed_lookups": lookups,
                    "indexed_seconds": round(indexed, 6),
                    "linear_sample_lookups": len(sample),
                    "linear_sample_seconds": round(linear, 6),
                    "db_bytes": path.stat().st_size}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, default=10000)
    parser.add_argument("--lookups", type=int, default=1000)
    args = parser.parse_args()
    if args.events < 1 or args.lookups < 1:
        parser.error("events and lookups must be positive")
    print(run(args.events, args.lookups))
