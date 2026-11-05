"""Minimal epistemic history ledger independent of the visual renderer.

Shared ledger used by unified checkpoints; automatic memory decay is not implemented.
"""
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Event:
    id: str
    year: int
    description: str
    witnesses: frozenset[int] = frozenset()

@dataclass(frozen=True)
class Claim:
    id: str
    event_id: str
    proposition: str
    source: str

@dataclass
class HistoricalLedger:
    events: dict[str, Event] = field(default_factory=dict)
    claims: dict[str, Claim] = field(default_factory=dict)
    knowledge: dict[int, set[str]] = field(default_factory=dict)

    def record(self, event: Event):
        if event.id in self.events or event.id in self.claims:
            raise ValueError("Duplicate event")
        self.events[event.id] = event
        for agent_id in event.witnesses:
            self.knowledge.setdefault(agent_id, set()).add(event.id)

    def publish_claim(self, claim: Claim):
        if claim.id in self.claims or claim.id in self.events:
            raise ValueError("Duplicate claim")
        if claim.event_id not in self.events:
            raise ValueError("Unknown referenced event")
        self.claims[claim.id] = claim

    def communicate(self, claim_id: str, recipient: int):
        if claim_id not in self.claims:
            raise ValueError("Unknown claim")
        self.knowledge.setdefault(recipient, set()).add(claim_id)

    def knows(self, agent_id: int, reference_id: str):
        return reference_id in self.knowledge.get(agent_id, set())
