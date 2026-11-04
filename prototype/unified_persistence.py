"""Lossless versioned JSON checkpoints for the unified reference kernel.

No pickle or eval. Saves are atomic; load validates essential invariants.
"""
import json
import os
from pathlib import Path
from borders import Route, Traveler
from discovery import Discovery, Researcher, Technique
from history import Claim, Event
from unified_kernel import UnifiedKernel, Pending
from world_state import KnowledgeClaim, Settlement
import heapq

VERSION = 1

def _tuple(value):
    return tuple(_tuple(x) for x in value) if isinstance(value, list) else value

def encode(world):
    state = {
        "version": VERSION, "rules_version": world.RULES_VERSION, "seed": world.seed, "day": world.day,
        "sequence": world.sequence, "rng": world.rng.getstate(),
        "settlements": [[s.id, s.region, s.resources, sorted(s.residents)] for s in world.state.settlements.values()],
        "routes": [[r.origin, r.destination, r.travel_days, r.hazard, r.restriction] for r in world.borders.routes.values()],
        "border_history": world.borders.history,
        "travelers": [[a.id, a.region, a.supplies, a.navigation, a.clearance, sorted(map(list, a.known_routes))] for a in world.travelers.values()],
        "researchers": [[a.id, sorted(a.knowledge), a.expertise] for a in world.discovery.researchers.values()],
        "techniques": [[t.id, sorted(t.traditions), sorted(t.prerequisites), t.difficulty] for t in world.discovery.techniques.values()],
        "discoveries": [[d.researcher_id, d.technique_id, list(d.source_knowledge)] for d in world.discovery.discoveries],
        "destiny": world.destiny, "locations": world.locations,
        "transit": sorted(world.transit), "destinations": world.destinations,
        "pending": [[d, s, e.kind, e.actor, e.target] for d,s,e in sorted(world.pending)],
        "events": [[e.id, e.year, e.description, sorted(e.witnesses)] for e in world.history.events.values()],
        "claims": [[c.id, c.event_id, c.proposition, c.source] for c in world.history.claims.values()],
        "history_knowledge": {str(k):sorted(v) for k,v in world.history.knowledge.items()},
        "world_claims": [[c.id,c.proposition,c.origin_event_id,list(c.evidence_ids)] for c in world.state.knowledge.values()],
        "beliefs": {str(k):sorted(v) for k,v in world.state.beliefs.items()},
        "outcomes": world.outcomes,
    }
    # Normalize tuple/list representations so live and restored states compare
    # identically and JSON roundtrips do not change canonical snapshots.
    return json.loads(json.dumps(state, sort_keys=True))

def decode(s):
    if s.get("version") != VERSION:
        raise ValueError("Unsupported unified checkpoint version")
    if s.get("rules_version") != UnifiedKernel.RULES_VERSION:
        raise ValueError("Unsupported simulation rules version")
    world = UnifiedKernel(s["seed"])
    world.day = s["day"]
    world.sequence = s["sequence"]
    world.rng.setstate(_tuple(s["rng"]))
    for sid,region,resources,residents in s["settlements"]:
        world.add_settlement(Settlement(sid,region,resources,set(residents)))
    for args in s["routes"]:
        world.add_route(Route(*args))
    world.borders.history = [tuple(x) for x in s["border_history"]]
    for args in s["techniques"]:
        tid,traditions,prereqs,difficulty = args
        world.add_technique(Technique(tid,frozenset(traditions),frozenset(prereqs),difficulty))
    for aid,region,supplies,navigation,clearance,routes in s["travelers"]:
        if aid in world.travelers:
            raise ValueError("Duplicate character")
        world.travelers[aid] = Traveler(aid,region,supplies,navigation,clearance,{tuple(r) for r in routes})
    for aid,knowledge,expertise in s["researchers"]:
        world.discovery.add_researcher(Researcher(aid,set(knowledge),expertise))
    world.discovery.discoveries = [Discovery(a,t,tuple(k)) for a,t,k in s["discoveries"]]
    world.destiny = {int(k):v for k,v in s["destiny"].items()}
    world.locations = {int(k):v for k,v in s["locations"].items()}
    world.transit = set(s["transit"])
    world.destinations = {int(k):v for k,v in s["destinations"].items()}
    world.pending = [(d,n,Pending(d,n,kind,actor,target)) for d,n,kind,actor,target in s["pending"]]
    heapq.heapify(world.pending)
    for eid,year,description,witnesses in s["events"]:
        world.history.record(Event(eid,year,description,frozenset(witnesses)))
    world.history.claims = {c[0]:Claim(*c) for c in s["claims"]}
    world.history.knowledge = {int(k):set(v) for k,v in s["history_knowledge"].items()}
    world.state.knowledge = {c[0]:KnowledgeClaim(c[0],c[1],c[2],tuple(c[3])) for c in s["world_claims"]}
    world.state.beliefs = {int(k):set(v) for k,v in s["beliefs"].items()}
    world.outcomes = [tuple(x) for x in s["outcomes"]]
    ids = set(world.travelers)
    if ids != set(world.discovery.researchers) or ids != set(world.destiny):
        raise ValueError("Inconsistent character registries")
    if set(world.locations) & world.transit or set(world.destinations) != world.transit:
        raise ValueError("Inconsistent transit state")
    if set(world.locations) | world.transit != ids:
        raise ValueError("Missing character location")
    if any(place not in world.state.settlements for place in world.locations.values()):
        raise ValueError("Unknown settlement location")
    for sid,place in world.state.settlements.items():
        expected = {aid for aid,location in world.locations.items() if location == sid}
        if place.residents != expected:
            raise ValueError("Inconsistent settlement residents")
    if any(d != e.day or n != e.sequence or e.actor not in ids or e.day < world.day or e.kind not in ("arrival", "research") for d,n,e in world.pending):
        raise ValueError("Invalid pending event")
    if len({n for _,n,_ in world.pending}) != len(world.pending):
        raise ValueError("Duplicate event sequence")
    if world.pending and world.sequence <= max(n for _,n,_ in world.pending):
        raise ValueError("Invalid event sequence")
    arrivals = {e.actor: e.target for _,_,e in world.pending if e.kind == "arrival"}
    if arrivals != world.destinations:
        raise ValueError("Inconsistent pending arrivals")
    if any(world.state.settlements[place].region != world.travelers[aid].region for aid,place in world.locations.items()):
        raise ValueError("Character region does not match residence")
    if any(e.kind == "research" and e.target not in world.discovery.techniques for _,_,e in world.pending):
        raise ValueError("Pending research references unknown technique")
    research_actors = [e.actor for _,_,e in world.pending if e.kind == "research"]
    if len(research_actors) != len(set(research_actors)):
        raise ValueError("Multiple pending research jobs for character")
    if any(d.researcher_id not in ids or d.technique_id not in world.discovery.techniques for d in world.discovery.discoveries):
        raise ValueError("Invalid discovery provenance")
    return world

def save(world, path):
    destination = Path(path)
    temporary = destination.with_name(destination.name + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as f:
            json.dump(encode(world),f,sort_keys=True,separators=(",",":"))
            f.flush()
            os.fsync(f.fileno())
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()

def load(path):
    with Path(path).open(encoding="utf-8") as f:
        return decode(json.load(f))
