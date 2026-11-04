"""Renderer-independent structured world facts and resource transfers.

This is a deterministic domain model; not yet wired into the event scheduler.
"""
from dataclasses import dataclass, field
from typing import Dict, Set

REGION_IDS = ("magic", "cultivation", "science", "primal", "superpowers", "nexus")

@dataclass
class Settlement:
    id: str
    region: str
    resources: Dict[str, int] = field(default_factory=dict)
    residents: Set[int] = field(default_factory=set)

    def __post_init__(self):
        if self.region not in REGION_IDS:
            raise ValueError("Unknown region")
        if any(not isinstance(v, int) or v < 0 for v in self.resources.values()):
            raise ValueError("Resources must be nonnegative integer quantities")

@dataclass(frozen=True)
class KnowledgeClaim:
    id: str
    proposition: str
    origin_event_id: str
    evidence_ids: tuple[str, ...] = ()
    # A claim is not necessarily an objectively true world fact.

class WorldState:
    def __init__(self):
        self.settlements: Dict[str, Settlement] = {}
        self.knowledge: Dict[str, KnowledgeClaim] = {}
        self.beliefs: Dict[int, Set[str]] = {}

    def add_settlement(self, settlement: Settlement):
        if settlement.id in self.settlements:
            raise ValueError("Duplicate settlement ID")
        self.settlements[settlement.id] = settlement

    def add_claim(self, claim: KnowledgeClaim):
        if claim.id in self.knowledge:
            raise ValueError("Duplicate knowledge claim ID")
        self.knowledge[claim.id] = claim

    def learn(self, agent_id: int, claim_id: str):
        if claim_id not in self.knowledge:
            raise KeyError("Unknown claim")
        self.beliefs.setdefault(agent_id, set()).add(claim_id)

    def transfer(self, source_id: str, target_id: str, resource: str, amount: int):
        if not isinstance(amount, int) or amount <= 0:
            raise ValueError("Transfer amount must be a positive integer")
        if source_id == target_id:
            raise ValueError("Source and destination must differ")
        source = self.settlements[source_id]
        target = self.settlements[target_id]
        available = source.resources.get(resource, 0)
        if available < amount:
            raise ValueError("Insufficient resources")
        source.resources[resource] = available - amount
        target.resources[resource] = target.resources.get(resource, 0) + amount
