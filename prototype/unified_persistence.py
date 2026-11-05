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
import tempfile
from invariants import validate
from checkpoint_schema import validate_shape

VERSION = 1

def _tuple(value):
    return tuple(_tuple(x) for x in value) if isinstance(value, list) else value

def encode(world):
    validate(world)
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
    """Reject malformed data before reconstruction; never migrate rules implicitly."""
    try:
        validate_shape(s)
        return _decode(s)
    except (KeyError, TypeError, IndexError, AttributeError, OverflowError) as exc:
        raise ValueError("Malformed unified checkpoint") from exc


def _decode(s):
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
    world._pending_research = {e.actor for _, _, e in world.pending if e.kind == "research"}
    for eid,year,description,witnesses in s["events"]:
        world.history.record(Event(eid,year,description,frozenset(witnesses)))
    world.history.claims = {c[0]:Claim(*c) for c in s["claims"]}
    world.history.knowledge = {int(k):set(v) for k,v in s["history_knowledge"].items()}
    world.state.knowledge = {c[0]:KnowledgeClaim(c[0],c[1],c[2],tuple(c[3])) for c in s["world_claims"]}
    world.state.beliefs = {int(k):set(v) for k,v in s["beliefs"].items()}
    world.outcomes = [tuple(x) for x in s["outcomes"]]
    validate(world)
    return world

def save(world, path):
    destination = Path(path)
    # Unique sibling files avoid collisions between independent save attempts.
    # The caller must serialize mutation of the live kernel while saving.
    state = encode(world)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                                         prefix=destination.name + ".", suffix=".tmp", delete=False) as f:
            temporary = Path(f.name)
            json.dump(state, f, sort_keys=True, separators=(",", ":"), allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key: " + key)
        result[key] = value
    return result


def _constant(value):
    raise ValueError("Non-finite JSON number: " + value)


def load(path):
    with Path(path).open(encoding="utf-8") as f:
        return decode(json.load(f, object_pairs_hook=_object, parse_constant=_constant))
