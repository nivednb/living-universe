"""Deterministic integrated world kernel: journeys, research, fate, and history.

Reference implementation, independent of the older sim.py and its checkpoints.
"""
from dataclasses import dataclass
import hashlib
import heapq
import json
import random
from borders import BorderWorld, Route, Traveler
from discovery import DiscoveryWorld, Researcher, Technique, Discovery
from history import Event, HistoricalLedger
from world_state import Settlement, WorldState

@dataclass(frozen=True)
class Pending:
    day: int
    sequence: int
    kind: str
    actor: int
    target: str

class UnifiedKernel:
    RULES_VERSION = 2

    def __init__(self, seed=42):
        if type(seed) is not int:
            raise ValueError("Seed must be an integer")
        self.seed = seed
        self.day = 0
        self.rng = random.Random(seed)
        self.sequence = 0
        self.pending = []
        self._pending_research = set()  # derived queue index, rebuilt on restore
        self.state = WorldState()
        self.borders = BorderWorld()
        self.discovery = DiscoveryWorld()
        self.history = HistoricalLedger()
        self.travelers = {}
        self.locations = {}
        self.transit = set()
        self.destinations = {}
        self.destiny = {}  # hidden individual influence; never directly shared as knowledge
        self.outcomes = []

    def add_settlement(self, place: Settlement):
        self.state.add_settlement(place)

    def add_route(self, route: Route):
        self.borders.add_route(route)

    def add_character(self, traveler: Traveler, researcher: Researcher, settlement_id: str, destiny=0):
        if traveler.id != researcher.id or traveler.id in self.travelers:
            raise ValueError("Character identifiers must match and be unique")
        if type(traveler.id) is not int or traveler.id < 0:
            raise ValueError("Character ID must be a nonnegative integer")
        if type(destiny) is not int or not -100 <= destiny <= 100:
            raise ValueError("Destiny must be in [-100, 100]")
        from invariants import integer
        if not (integer(traveler.supplies, 0) and integer(traveler.navigation, 0, 100)
                and integer(traveler.clearance, 0, 100)
                and all(isinstance(k, str) and integer(v, 0) for k, v in researcher.expertise.items())
                and researcher.knowledge <= self.discovery.techniques.keys()):
            raise ValueError("Invalid character attributes or knowledge")
        place = self.state.settlements[settlement_id]
        if traveler.region != place.region:
            raise ValueError("Region mismatch")
        if traveler.id in self.discovery.researchers or any(traveler.id in s.residents for s in self.state.settlements.values()):
            raise ValueError("Character already registered")
        self.discovery.add_researcher(researcher)
        self.travelers[traveler.id] = traveler
        self.locations[traveler.id] = settlement_id
        self.destiny[traveler.id] = destiny
        place.residents.add(traveler.id)

    def add_technique(self, technique: Technique):
        self.discovery.add_technique(technique)

    def _enqueue(self, day, kind, actor, target):
        event = Pending(day, self.sequence, kind, actor, target)
        self.sequence += 1
        heapq.heappush(self.pending, (event.day, event.sequence, event))
        if kind == "research":
            self._pending_research.add(actor)

    def depart(self, actor: int, destination_settlement: str):
        if actor in self.transit:
            raise ValueError("Already traveling")
        traveler = self.travelers[actor]
        if actor not in self.locations:
            raise ValueError("Traveler has no origin settlement")
        origin = self.state.settlements[self.locations[actor]]
        if actor not in origin.residents or traveler.region != origin.region:
            raise ValueError("Traveler residence is inconsistent")
        destination = self.state.settlements[destination_settlement]
        result = self.borders.travel(traveler, destination.region)
        if not result.accepted:
            return result
        # The border model immediately updates region; the kernel delays it to arrival.
        traveler.region = self.state.settlements[self.locations[actor]].region
        self.state.settlements[self.locations[actor]].residents.remove(actor)
        self.locations.pop(actor)
        self.transit.add(actor)
        self.destinations[actor] = destination_settlement
        self._enqueue(self.day + result.days, "arrival", actor, destination_settlement)
        self._record("departure", actor, f"Departed toward {destination_settlement}")
        return result

    def research(self, actor: int, technique_id: str, days: int):
        if type(days) is not int or days <= 0:
            raise ValueError("Research duration must be positive")
        researcher = self.discovery.researchers[actor]
        technique = self.discovery.techniques[technique_id]
        if technique_id in researcher.knowledge or not technique.prerequisites.issubset(researcher.knowledge):
            raise ValueError("Prerequisites missing or technique already known")
        if actor in self._pending_research:
            raise ValueError("Research already pending")
        self._enqueue(self.day + days, "research", actor, technique_id)
        self._record("research_start", actor, f"Research began: {technique_id}")

    def teach(self, teacher: int, student: int, technique_id: str):
        if not self.discovery.teach(teacher, student, technique_id):
            return False
        self._record("teaching", teacher, f"Taught {technique_id} to {student}", {teacher, student})
        return True

    def advance(self, days: int):
        if type(days) is not int or days < 0:
            raise ValueError("Days must be nonnegative")
        end = self.day + days
        while self.pending and self.pending[0][0] <= end:
            when, _, item = heapq.heappop(self.pending)
            self.day = when
            if item.kind == "arrival":
                self.transit.remove(item.actor)
                destination = self.destinations.pop(item.actor)
                self.locations[item.actor] = destination
                place = self.state.settlements[destination]
                place.residents.add(item.actor)
                self.travelers[item.actor].region = place.region
                self._record("arrival", item.actor, f"Arrived at {destination}")
            elif item.kind == "research":
                self._pending_research.remove(item.actor)
                researcher = self.discovery.researchers[item.actor]
                technique = self.discovery.techniques[item.target]
                expertise = sum(researcher.expertise.get(t, 0) for t in technique.traditions)
                # A deterministic seeded draw, influenced but not dictated by destiny.
                roll = self.rng.randrange(100)
                chance = max(5, min(95, 50 + 5 * (expertise - technique.difficulty) + self.destiny[item.actor] // 5))
                success = (item.target not in researcher.knowledge
                           and technique.prerequisites.issubset(researcher.knowledge) and roll < chance)
                if success:
                    researcher.knowledge.add(item.target)
                    self.discovery.discoveries.append(Discovery(item.actor, item.target, tuple(sorted(technique.prerequisites))))
                self.outcomes.append((when, item.actor, item.target, success, roll, chance))
                self._record("discovery" if success else "research_failure", item.actor, item.target)
            else:
                raise ValueError("Unknown event type")
        self.day = end

    def _record(self, kind, actor, detail, witnesses=None):
        index = len(self.history.events)
        event_id = f"kernel-{index}"
        while event_id in self.history.events or event_id in self.history.claims:
            index += 1
            event_id = f"kernel-{index}"
        self.history.record(Event(event_id, self.day, f"{kind}: {detail}", frozenset({actor} if witnesses is None else witnesses)))

    def validate(self):
        """Check registry, knowledge, residency and scheduler invariants."""
        from invariants import validate
        validate(self)

    def snapshot(self):
        # Complete versioned state, including routes, beliefs, witnesses, RNG,
        # event sequence and pending actions. Shared with checkpoint persistence.
        from unified_persistence import encode
        return encode(self)

    def digest(self):
        return hashlib.sha256(json.dumps(self.snapshot(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
