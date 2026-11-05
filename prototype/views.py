"""Detached read models for renderers; never drive the simulation clock.

Observer access is privileged. These functions do not perform authentication;
the application must authorize observer access and bind character identity.
Authoritative checkpoints are deliberately not used as client messages.
"""
from dataclasses import asdict, dataclass
import json

VIEW_VERSION = 1


@dataclass(frozen=True)
class ActorView:
    id: int
    region: str
    settlement_id: str | None
    destination_id: str | None
    arrival_day: int | None


@dataclass(frozen=True)
class SettlementView:
    id: str
    region: str
    resources: tuple[tuple[str, int], ...]
    residents: tuple[int, ...]


@dataclass(frozen=True)
class RouteView:
    origin_region: str
    destination_region: str
    travel_days: int


@dataclass(frozen=True)
class ObserverView:
    version: int
    day: int
    settlements: tuple[SettlementView, ...]
    actors: tuple[ActorView, ...]
    routes: tuple[RouteView, ...]


@dataclass(frozen=True)
class RememberedEvent:
    id: str
    day: int
    description: str


@dataclass(frozen=True)
class HeardClaim:
    id: str
    proposition: str
    source: str


@dataclass(frozen=True)
class BeliefView:
    id: str
    proposition: str


@dataclass(frozen=True)
class CharacterView:
    version: int
    day: int
    actor: ActorView
    techniques: tuple[str, ...]
    remembered_events: tuple[RememberedEvent, ...]
    heard_claims: tuple[HeardClaim, ...]
    beliefs: tuple[BeliefView, ...]


def _actor(world, actor, arrivals):
    traveler = world.travelers[actor]
    return ActorView(actor, traveler.region, world.locations.get(actor),
                     world.destinations.get(actor), arrivals.get(actor))


def observer_view(world, *, actor_ids=None):
    """Privileged world graph, optionally selecting actor records for rendering.

    Filtering actor records does not restrict settlement or route disclosure.
    This is a presentation filter, never an authorization or simulation boundary.
    All objects are detached and collections are sorted for stable output.
    """
    selected = tuple(world.travelers) if actor_ids is None else tuple(actor_ids)
    if any(type(actor) is not int or actor not in world.travelers for actor in selected):
        raise ValueError("Unknown observer actor selection")
    arrivals = {event.actor: day for day, _, event in world.pending if event.kind == "arrival"}
    return ObserverView(
        VIEW_VERSION, world.day,
        tuple(SettlementView(s.id, s.region, tuple(sorted(s.resources.items())), tuple(sorted(s.residents)))
              for _, s in sorted(world.state.settlements.items())),
        tuple(_actor(world, actor, arrivals) for actor in sorted(set(selected))),
        tuple(RouteView(r.origin, r.destination, r.travel_days)
              for _, r in sorted(world.borders.routes.items())),
    )


def character_view(world, actor):
    """Only self state and acquired knowledge; no global observer data.

    Communicated claims expose their statements, not the truth of their origin
    events or private evidence. World beliefs similarly expose propositions only.
    There is no proximity/perception model yet, so nearby actors are not included.
    """
    if type(actor) is not int or actor not in world.travelers:
        raise ValueError("Unknown character")
    arrivals = {event.actor: day for day, _, event in world.pending
                if event.kind == "arrival" and event.actor == actor}
    known = world.history.knowledge.get(actor, set())
    return CharacterView(
        VIEW_VERSION, world.day, _actor(world, actor, arrivals),
        tuple(sorted(world.discovery.researchers[actor].knowledge)),
        tuple(RememberedEvent(eid, world.history.events[eid].year, world.history.events[eid].description)
              for eid in sorted(known) if eid in world.history.events),
        tuple(HeardClaim(cid, world.history.claims[cid].proposition, world.history.claims[cid].source)
              for cid in sorted(known) if cid in world.history.claims),
        tuple(BeliefView(cid, world.state.knowledge[cid].proposition)
              for cid in sorted(world.state.beliefs.get(actor, set()))),
    )


def to_wire(view):
    """Fresh JSON-compatible message with an explicit disclosure scope."""
    if type(view) not in (ObserverView, CharacterView):
        raise TypeError("Expected a renderer view, not an authoritative snapshot")
    message = asdict(view)
    message["scope"] = "observer" if type(view) is ObserverView else "character"
    return json.loads(json.dumps(message, sort_keys=True, allow_nan=False))
