# Temporal observation windows and bounded historical reconstruction

Status: **design decision / phased implementation**, not yet an integrated observer runtime.

## Decision

Separate the **authoritative simulation clock** from any number of **read-only observer clocks**. The simulator advances causal world state; observers can independently inspect historical states without mutating the simulator, consuming its RNG, or changing its event sequence. An observer's in-memory cache is bounded by **bytes**, not by a fixed number of simulated years.

## Reconstruction contract

1. Select the newest compatible checkpoint at or before the requested observation time.
2. Restore it in an isolated read-only reconstruction context.
3. Apply or replay every required, ordered, version-compatible event to the observation time. A historical log of descriptions alone is **not sufficient** to reconstruct state.
4. Resolve a requested spatial region, entities and level of detail, plus dependencies crossing the requested boundary.
5. Prefetch adjacent time/space segments within a configurable memory budget; evict least-recently-used reconstructed views without deleting authoritative data.
6. If no complete checkpoint + state transitions / deterministic replay inputs are available, report the time as **not exactly reconstructable**. Never invent missing history.

## Important distinction

The existing `prototype/history.py` ledger stores human-readable historical events and epistemic claims. It is **not a state-delta log**. `prototype/sqlite_history.py` currently archives events without enabling deterministic world reconstruction. The current unified JSON checkpoint is complete but embeds history and agent knowledge; it is not yet a bounded-memory architecture.

Agent knowledge/beliefs may depend on historical references; references must remain resolvable even when historical event objects are evicted from RAM. Observer cache eviction must not alter authoritative causality, RNG or epistemic knowledge.

## Incremental plan

- **P0:** verify exact lossless history export and SQLite corruption/transaction tests; ensure CI remains green.
- **P1:** add a read-only historical event window API with bounded streaming and explicit cursor/time range; test independent observers, window movement and cache eviction. This is archival **viewing**, not state reconstruction.
- **P2:** introduce an explicit versioned causal state-transition log or replay contract, checkpoint index and compatibility checks; guarantee exact restoration at arbitrary supported times.
- **P3:** decouple history from live checkpoints, preserve event references and knowledge, enforce memory budgets, benchmark at 100–5000 agents and long runs.
- **P4:** selectively materialize spatial/entity subsets only after proving dependencies are complete. Avoid misleading claims that off-screen entities can be ignored in authoritative simulation.

## Measurement gates

Track peak RSS, bytes of retained historical objects, database size, observer seek latency (cold/warm), window movement throughput, read amplification, checkpoint overhead, exact replay equality and behavior under simulated crash/restart. Compare with existing JSON checkpoints and the opt-in SQLite archive before committing to further complexity.

## Established foundations

- SQLite WAL: https://www.sqlite.org/wal.html
- Event sourcing and snapshots: https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing
- Bitemporal history: https://martinfowler.com/articles/bitemporal-history.html
- Existing storage research: `docs/architecture/lossless-storage-research.md`
