# Architecture

## Implemented reference boundary

The standard-library Python prototype now integrates a deterministic event queue,
travel, research, knowledge, history, versioned checkpoints and validated read
models. `prototype/views.py` exposes detached observer and character projections;
viewers do not drive the clock or affect which world events execute. See the
[view contract and future 3D boundary](view-contract.md) and
[foundation verification](foundation-stability.md). This is still a reference
implementation, not a production server or playable client.

## Proposed production boundaries
- `packages/world-rules`: versioned physical and fantasy mechanics, field interactions, validation.
- `packages/agents`: identities, needs, goals, skills, beliefs, memories, action proposals.
- `packages/simulation`: authoritative state transitions, scheduling, resource and environmental effects.
- `packages/history`: causal events, snapshots, provenance, reproducible replay and experiments.
- `packages/shared`: schemas and client-facing contracts.
- `apps/observer`: timelines, world maps, histories, comparisons and intervention tools.
- `apps/rpg`: top-down player interactions and visualization of the same world state.

## Operating model
Persistent server-authoritative simulation, multiresolution agent scheduling, deterministic seeds and versioned rules. Routine decisions use inexpensive algorithms; advanced planning and dialogue may use optional AI with all actions validated by the simulation. Observer attention must not determine whether a consequential event is simulated.

## Technology status
Mesa, Aurelia, Source of Mana and alternatives are **candidates only**, not selected dependencies. Evaluate licenses, maintenance, interoperability, reproducibility, web deployment and agent-count benchmarks before adoption. No performance guarantees are implied.

## Nonfunctional goals
Low-cost local development, optional self-hosting, testable modules, clear attribution, schema migrations, automated checks, replay integrity and minimal unnecessary infrastructure.
