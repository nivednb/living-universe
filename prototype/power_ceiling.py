"""Versioned simulation capability ceilings, separate from fictional power.

A capability may exist in lore while its detailed simulation remains unsupported.
"""
from dataclasses import dataclass, field

@dataclass(frozen=True)
class EngineCapabilities:
    version: int
    supported: frozenset[str]

    def __post_init__(self):
        if self.version < 1:
            raise ValueError("Capability version must be positive")

@dataclass
class ActorPower:
    actor_id: int
    unlocked: set[str] = field(default_factory=set)

@dataclass(frozen=True)
class PowerDecision:
    permitted: bool
    reason: str
    fidelity: str

def evaluate(actor: ActorPower, capability: str, engine: EngineCapabilities) -> PowerDecision:
    if capability not in actor.unlocked:
        return PowerDecision(False, "actor_lacks_capability", "none")
    if capability not in engine.supported:
        return PowerDecision(False, "unsupported_by_engine", "abstract")
    return PowerDecision(True, "supported", "detailed")
