"""Deterministic travel decisions with imperfect route knowledge.

Shared domain model used by unified_kernel; independent of the legacy Universe.
"""
from dataclasses import dataclass, field
from typing import Dict, Set, Tuple

@dataclass(frozen=True)
class Route:
    origin: str
    destination: str
    travel_days: int
    hazard: int = 0
    restriction: int = 0

    def __post_init__(self):
        if self.origin == self.destination or type(self.travel_days) is not int or self.travel_days <= 0:
            raise ValueError("Route needs distinct endpoints and positive travel time")
        if not (type(self.hazard) is int and type(self.restriction) is int
                and 0 <= self.hazard <= 100 and 0 <= self.restriction <= 100):
            raise ValueError("Hazard and restriction must be percentages")

@dataclass
class Traveler:
    id: int
    region: str
    supplies: int
    navigation: int
    clearance: int = 0
    known_routes: Set[Tuple[str, str]] = field(default_factory=set)

@dataclass(frozen=True)
class TravelResult:
    accepted: bool
    reason: str
    days: int = 0

class BorderWorld:
    def __init__(self):
        self.routes: Dict[Tuple[str, str], Route] = {}
        self.history: list[tuple[int, str, str, bool, str]] = []

    def add_route(self, route: Route):
        key = (route.origin, route.destination)
        if key in self.routes:
            raise ValueError("Duplicate route")
        self.routes[key] = route

    def travel(self, traveler: Traveler, destination: str):
        key = (traveler.region, destination)
        route = self.routes.get(key)
        if route is None:
            outcome = TravelResult(False, "no_route")
        elif key not in traveler.known_routes:
            outcome = TravelResult(False, "unknown_route")
        elif traveler.supplies < route.travel_days:
            outcome = TravelResult(False, "insufficient_supplies")
        elif traveler.clearance < route.restriction:
            outcome = TravelResult(False, "restricted")
        elif traveler.navigation < route.hazard:
            outcome = TravelResult(False, "hazard")
        else:
            traveler.supplies -= route.travel_days
            traveler.region = destination
            outcome = TravelResult(True, "arrived", route.travel_days)
        self.history.append((traveler.id, key[0], destination, outcome.accepted, outcome.reason))
        return outcome
