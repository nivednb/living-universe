"""Read-only resolver for historical references stored in SQLite."""
from archived_events import ArchivedEvents


class ArchivedReferenceResolver:
    def __init__(self, ledger, claims):
        self.events = ArchivedEvents(ledger)
        self.claims = claims

    def event_exists(self, event_id):
        return event_id in self.events

    def reference_exists(self, reference_id):
        return reference_id in self.claims or self.event_exists(reference_id)

    def resolve_claim_event(self, claim_id):
        return self.events[self.claims[claim_id].event_id]

    def knows(self, knowledge, actor_id, reference_id):
        return reference_id in knowledge.get(actor_id, ()) and self.reference_exists(reference_id)

    def validate_claim_references(self):
        for claim_id, claim in self.claims.items():
            if claim.id != claim_id or not self.event_exists(claim.event_id):
                raise ValueError(f"invalid historical reference in claim {claim_id}")
        return len(self.claims)
