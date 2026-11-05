"""Standard-library synthetic integration benchmark, not a capacity claim.

Run: python benchmark_unified.py --agents 1000 --rounds 100
Each round schedules one journey and one research job per actor. Checkpoint
continuation is compared with an uninterrupted run, including simultaneous jobs.
"""
import argparse
import json
import platform
import resource
import tempfile
from pathlib import Path
from time import perf_counter

from borders import Route, Traveler
from discovery import Researcher, Technique
from unified_kernel import UnifiedKernel
from unified_persistence import load, save
from world_state import REGION_IDS, Settlement


def build(agents, seed=42):
    world = UnifiedKernel(seed)
    for region in REGION_IDS:
        world.add_settlement(Settlement(region, region))
        if region != "nexus":
            world.add_route(Route(region, "nexus", 5))
            world.add_route(Route("nexus", region, 5))
    for actor in range(agents):
        region = REGION_IDS[actor % 5]
        world.add_character(Traveler(actor, region, 10**9, 100, 100,
                                     {(region, "nexus"), ("nexus", region)}),
                            Researcher(actor, expertise={region: 10}), region, (actor % 201) - 100)
    return world


def schedule(world, iteration):
    technique = "study-" + str(iteration)
    world.add_technique(Technique(technique, frozenset({"science", "magic"}), difficulty=8))
    for actor in world.travelers:
        destination = "nexus" if iteration % 2 == 0 else REGION_IDS[actor % 5]
        world.depart(actor, destination)
        world.research(actor, technique, 3 + actor % 3 * 2)


def run(agents, rounds, seed=42):
    start = perf_counter()
    reference = build(agents, seed)
    setup_seconds = perf_counter() - start
    start = perf_counter()
    for iteration in range(rounds):
        schedule(reference, iteration)
        reference.advance(10)
    simulation_seconds = perf_counter() - start
    start = perf_counter()
    reference.validate()
    validation_seconds = perf_counter() - start
    expected = reference.digest()
    event_count = reference.sequence
    history_count = len(reference.history.events)
    del reference

    # Re-run with a real JSON checkpoint taken during travel and research.
    resumed = build(agents, seed)
    midpoint = rounds // 2
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "world.json"
        for iteration in range(rounds):
            schedule(resumed, iteration)
            if iteration == midpoint:
                resumed.advance(3)
                start = perf_counter()
                save(resumed, path)
                save_seconds = perf_counter() - start
                checkpoint_bytes = path.stat().st_size
                start = perf_counter()
                resumed = load(path)
                load_seconds = perf_counter() - start
                resumed.advance(7)
            else:
                resumed.advance(4)
                resumed.advance(6)
    resumed.validate()
    if resumed.digest() != expected:
        raise AssertionError("Checkpoint or incremental continuation diverged")
    return {"python": platform.python_version(), "platform": platform.platform(),
            "rules_version": resumed.RULES_VERSION, "seed": seed, "agents": agents,
            "rounds": rounds, "days": resumed.day, "scheduled_events": event_count,
            "history_events": history_count, "setup_seconds": round(setup_seconds, 6),
            "simulation_seconds": round(simulation_seconds, 6),
            "events_per_second": round(event_count / simulation_seconds),
            "validation_seconds": round(validation_seconds, 6),
            "checkpoint_bytes": checkpoint_bytes, "save_seconds": round(save_seconds, 6),
            "load_seconds": round(load_seconds, 6),
            "peak_rss_kib_linux": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "continuation_equal": True, "digest": expected}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agents", type=int, default=1000)
    parser.add_argument("--rounds", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.agents < 1 or args.rounds < 1:
        parser.error("agents and rounds must be positive")
    print(json.dumps(run(args.agents, args.rounds, args.seed), sort_keys=True, indent=2))
