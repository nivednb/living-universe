# World-state contracts — initial implementation

The `prototype/world_state.py` domain module separates world facts from a rendered map. It currently models stable settlement identifiers, region membership, nonnegative resource inventories, resource-conserving transfers, provenance-linked knowledge claims and per-agent beliefs.

**Important limitations:** This is a standalone reference model, not yet integrated into the main simulation scheduler or persistence. It has no transactions across processes, markets, production, depletion, climate, real geography, true-versus-false claim adjudication, or permission system. Tests cover local invariants only.

The design allows future 2D and 3D clients to read a common authoritative state without coupling simulation to either renderer. Next: versioned event schema, integration of resource events with deterministic replay, cross-region movement, and snapshot migration.
