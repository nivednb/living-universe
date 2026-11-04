"""Versioned JSON checkpoint/restore for the reference scheduler.

This is a reference format, not yet a durable production database.
"""
import json
from pathlib import Path
from sim import Agent, Universe

SCHEMA_VERSION = 1

def _tuples(value):
    if isinstance(value, list):
        return tuple(_tuples(x) for x in value)
    return value

def save(world: Universe, path):
    state = world.snapshot()
    # The reference prototype exposes RNG state via repr; checkpoint the
    # actual structured RNG state instead, without eval/pickle.
    state["rng_state"] = world.rng.getstate()
    state["schema_version"] = SCHEMA_VERSION
    dest = Path(path)
    tmp = dest.with_name(dest.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        json.dump(state, stream, sort_keys=True, separators=(",", ":"))
        stream.flush()
        import os
        os.fsync(stream.fileno())
    tmp.replace(dest)

def load(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        state = json.load(stream)
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported checkpoint schema version")
    agents = state["agents"]
    if len({a["id"] for a in agents}) != len(agents):
        raise ValueError("Duplicate agent identifiers")
    world = Universe(0, state["seed"])
    world.day = state["day"]
    world.agents = {item["id"]: Agent(**item) for item in agents}
    world.events = [tuple(event) for event in state["events"]]
    world.rng.setstate(_tuples(state["rng_state"]))
    import heapq
    world.queue = [(a.next_action, a.id) for a in world.agents.values()]
    heapq.heapify(world.queue)
    return world
