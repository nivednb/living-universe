"""Integrated-kernel consistency checks; no mutation or random draws.

The standalone domain models permit external knowledge labels. The integrated
kernel requires registered techniques, actors, events and claims at checkpoints.
"""
from world_state import REGION_IDS


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, minimum=None, maximum=None):
    return (type(value) is int and (minimum is None or value >= minimum)
            and (maximum is None or value <= maximum))


def validate(world):
    """Raise ValueError on broken invariants, in O(state + pending events)."""
    require(integer(world.seed), "Seed must be an integer")
    require(integer(world.day, 0) and integer(world.sequence, 0), "Invalid clock or sequence")
    ids = set(world.travelers)
    techniques = world.discovery.techniques
    require(all(integer(a, 0) for a in ids), "Invalid character identifier")
    require(ids == set(world.discovery.researchers) == set(world.destiny), "Inconsistent character registries")
    require(set(world.locations).isdisjoint(world.transit)
            and set(world.locations) | world.transit == ids
            and set(world.destinations) == world.transit, "Inconsistent character locations")
    expected = {sid: set() for sid in world.state.settlements}
    for actor, sid in world.locations.items():
        require(sid in expected, "Unknown settlement location")
        expected[sid].add(actor)
        require(world.travelers[actor].region == world.state.settlements[sid].region,
                "Character region does not match residence")
    require(all(sid in expected for sid in world.destinations.values()), "Unknown travel destination")
    for sid, place in world.state.settlements.items():
        require(isinstance(sid, str) and bool(sid) and place.id == sid
                and place.region in REGION_IDS, "Invalid settlement")
        require(place.residents == expected[sid], "Inconsistent settlement residents")
        require(all(isinstance(k, str) and integer(v, 0) for k, v in place.resources.items()),
                "Invalid resource quantities")
    for actor, traveler in world.travelers.items():
        researcher = world.discovery.researchers[actor]
        require(traveler.id == researcher.id == actor and traveler.region in REGION_IDS,
                "Invalid character identity or region")
        require(integer(traveler.supplies, 0) and integer(traveler.navigation, 0, 100)
                and integer(traveler.clearance, 0, 100) and integer(world.destiny[actor], -100, 100),
                "Invalid character attributes")
        require(researcher.knowledge <= techniques.keys(), "Unknown character technique")
        require(all(isinstance(k, str) and integer(v, 0) for k, v in researcher.expertise.items()),
                "Invalid expertise")
        require(all(len(r) == 2 and all(x in REGION_IDS for x in r) for r in traveler.known_routes),
                "Invalid known route")
    for key, route in world.borders.routes.items():
        require(key == (route.origin, route.destination) and route.origin in REGION_IDS
                and route.destination in REGION_IDS and route.origin != route.destination,
                "Invalid route endpoints")
        require(integer(route.travel_days, 1) and integer(route.hazard, 0, 100)
                and integer(route.restriction, 0, 100), "Invalid route attributes")
    for actor, origin, destination, accepted, reason in world.borders.history:
        require(actor in ids and origin in REGION_IDS and destination in REGION_IDS
                and type(accepted) is bool and reason in {"arrived", "no_route", "unknown_route",
                                                         "insufficient_supplies", "restricted", "hazard"}
                and accepted == (reason == "arrived"), "Invalid border history")
    for tid, technique in techniques.items():
        require(isinstance(tid, str) and bool(tid) and technique.id == tid
                and bool(technique.traditions) and all(isinstance(t, str) for t in technique.traditions)
                and integer(technique.difficulty, 0), "Invalid technique")
        require(technique.prerequisites <= techniques.keys() and tid not in technique.prerequisites,
                "Invalid technique prerequisites")
    sequences, arrivals, researchers = set(), {}, set()
    for index, (day, sequence, event) in enumerate(world.pending):
        require(integer(day, world.day) and integer(sequence, 0) and sequence < world.sequence
                and sequence not in sequences and day == event.day and sequence == event.sequence
                and event.actor in ids, "Invalid pending event")
        sequences.add(sequence)
        if index:
            require(world.pending[(index - 1) // 2][:2] <= (day, sequence), "Invalid event heap")
        if event.kind == "arrival":
            require(event.actor not in arrivals and event.target in expected, "Invalid or duplicate arrival")
            arrivals[event.actor] = event.target
        elif event.kind == "research":
            require(event.actor not in researchers and event.target in techniques, "Invalid pending research")
            require(techniques[event.target].prerequisites <= world.discovery.researchers[event.actor].knowledge,
                    "Pending research prerequisites missing")
            researchers.add(event.actor)
        else:
            raise ValueError("Unknown pending event kind")
    require(arrivals == world.destinations, "Inconsistent pending arrivals")
    require(researchers == world._pending_research, "Inconsistent research queue index")
    discoveries = set()
    for discovery in world.discovery.discoveries:
        key = (discovery.researcher_id, discovery.technique_id)
        require(key not in discoveries and key[0] in ids and key[1] in techniques, "Invalid discovery provenance")
        discoveries.add(key)
        knowledge = world.discovery.researchers[key[0]].knowledge
        require(key[1] in knowledge and discovery.source_knowledge == tuple(sorted(techniques[key[1]].prerequisites))
                and set(discovery.source_knowledge) <= knowledge, "Invalid discovery source knowledge")
    events, claims = world.history.events, world.history.claims
    historical_references = events.keys() | claims.keys()
    require(events.keys().isdisjoint(claims), "Ambiguous historical reference")
    for eid, event in events.items():
        require(isinstance(eid, str) and bool(eid) and event.id == eid
                and integer(event.year) and event.year <= world.day and event.witnesses <= ids,
                "Invalid historical event")
        require(all(eid in world.history.knowledge.get(a, set()) for a in event.witnesses),
                "Missing witness memory")
    for cid, claim in claims.items():
        require(claim.id == cid and claim.event_id in events, "Invalid historical claim")
    for actor, references in world.history.knowledge.items():
        require(actor in ids and references <= historical_references, "Invalid historical knowledge")
        require(all(actor in events[r].witnesses for r in references if r in events),
                "Unwitnessed event presented as direct knowledge")
    evidence_references = historical_references | world.state.knowledge.keys()
    for cid, claim in world.state.knowledge.items():
        require(claim.id == cid and claim.origin_event_id in events
                and set(claim.evidence_ids) <= evidence_references,
                "Invalid world claim provenance")
    for actor, beliefs in world.state.beliefs.items():
        require(actor in ids and beliefs <= world.state.knowledge.keys(), "Invalid beliefs")
    previous_day = 0
    successes = set()
    for day, actor, target, success, roll, chance in world.outcomes:
        require(integer(day, 0, world.day) and actor in ids and target in techniques
                and type(success) is bool and integer(roll, 0, 99) and integer(chance, 5, 95),
                "Invalid research outcome")
        require(day >= previous_day, "Unordered research outcomes")
        previous_day = day
        if success:
            require(roll < chance and (actor, target) in discoveries and (actor, target) not in successes,
                    "Invalid successful discovery outcome")
            successes.add((actor, target))
