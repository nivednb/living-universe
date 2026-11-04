"""Event-scheduled travel with recorded history and settlement membership.

Standalone integrated vertical slice. The full Universe scheduler and checkpoint
format are not yet connected to this module.
"""
from dataclasses import dataclass
import heapq
from borders import BorderWorld, Traveler
from history import Event, HistoricalLedger
from world_state import WorldState

@dataclass(frozen=True)
class Journey:
    traveler_id: int
    origin: str
    destination: str
    departure_day: int
    arrival_day: int

class TravelSimulation:
    def __init__(self, borders: BorderWorld, state: WorldState, history: HistoricalLedger):
        self.borders = borders
        self.state = state
        self.history = history
        self.day = 0
        self.travelers: dict[int, Traveler] = {}
        self.in_transit: dict[int, Journey] = {}
        self.pending: list[tuple[int, int]] = []
        self.sequence = 0

    def register(self, traveler: Traveler, settlement_id: str):
        if traveler.id in self.travelers:
            raise ValueError("Duplicate traveler")
        settlement = self.state.settlements[settlement_id]
        if traveler.region != settlement.region:
            raise ValueError("Traveler and settlement region mismatch")
        if traveler.id in self.in_transit:
            raise ValueError("Traveler already in transit")
        self.travelers[traveler.id] = traveler
        settlement.residents.add(traveler.id)

    def depart(self, traveler_id: int, destination: str, destination_settlement: str):
        if traveler_id in self.in_transit:
            raise ValueError("Traveler already in transit")
        traveler = self.travelers[traveler_id]
        destination_place = self.state.settlements[destination_settlement]
        if destination_place.region != destination:
            raise ValueError("Destination settlement and region mismatch")
        origins = [s for s in self.state.settlements.values() if traveler_id in s.residents]
        if len(origins) != 1:
            raise ValueError("Traveler must occupy exactly one origin settlement")
        origin_place = origins[0]
        # BorderWorld.travel mutates the traveler on success; restore its region
        # until arrival so location is not prematurely committed.
        origin_region = traveler.region
        result = self.borders.travel(traveler, destination)
        if not result.accepted:
            return result
        traveler.region = origin_region
        origin_place.residents.remove(traveler_id)
        arrival = self.day + result.days
        journey = Journey(traveler_id, origin_place.id, destination_settlement, self.day, arrival)
        self.in_transit[traveler_id] = journey
        heapq.heappush(self.pending, (arrival, traveler_id))
        self._record(traveler_id, "departure", origin_region, self.day)
        return result

    def advance(self, days: int):
        if not isinstance(days, int) or days < 0:
            raise ValueError("Days must be nonnegative")
        end = self.day + days
        while self.pending and self.pending[0][0] <= end:
            when, traveler_id = heapq.heappop(self.pending)
            journey = self.in_transit.pop(traveler_id)
            destination = self.state.settlements[journey.destination]
            traveler = self.travelers[traveler_id]
            traveler.region = destination.region
            destination.residents.add(traveler_id)
            self._record(traveler_id, "arrival", destination.region, when)
        self.day = end

    def _record(self, traveler_id: int, kind: str, region: str, day: int):
        event_id = f"travel-{self.sequence}"
        self.sequence += 1
        self.history.record(Event(event_id, day, f"{kind}: agent {traveler_id} in {region}", frozenset({traveler_id})))
