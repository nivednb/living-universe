# Viewer-independent simulation and future 3D support

**Status:** Architectural decision for follow-up work (2026-11-05). This is a design target, not a claim that the interfaces or 3D viewer are implemented.

## Decision
Living Universe has **one authoritative persistent simulation** and can have multiple interchangeable clients: the originally planned 2D RPG, a browser-based 3D planetary observer, and potentially VR. Rendering technology must not determine the world's authoritative rules.

## Responsibility boundaries
- **Simulation/kernel:** identities, agents, civilization and world rules, authoritative state transitions, persistent changes, deterministic event ordering, history and checkpoints. The simulation is independent of any viewer.
- **Shared world representation/contracts:** stable entity IDs; region, settlement and entity positions; spatial relationships; time and versioned state snapshots/deltas; reproducible generation seeds and version identifiers. Spatial fidelity should grow only when mechanics require it. Coordinates must be well-defined but need not force a specific renderer, planet model, or 2D tile grid.
- **Viewers:** 2D sprites, 3D terrain/buildings, animation, LOD, instancing, local decorative crowds and effects. Decorative geometry can be derived procedurally without becoming authoritative simulation state. A viewer may generate consistent detail using shared seeds and versioned generation rules.
- **Authoritative world changes:** a destroyed mountain, new settlement, character death, traversable building or other consequential change must be represented in authoritative state/events, not only a client visual. The viewer may embellish how that change looks.

## Performance and persistence
- Adding a 3D viewer need not increase **simulation** workload if it consumes existing state, although it increases client rendering cost and may add server/network/API load.
- More fine-grained *mechanics* (per-person routes, detailed interiors, collision) do increase simulation and persistence requirements, irrespective of 2D or 3D rendering.
- Use multiresolution simulation and interest-based state delivery, with distant regions represented compactly. Observer attention must not change consequential outcomes.
- The simulation continues without an open browser only while its host is running; static hosting such as GitHub Pages can serve the viewer but cannot itself run an always-on Python simulation.

## Recommended incremental work
1. Continue stabilizing the existing Python kernel, deterministic replay and checkpoint tests. Review the open stabilization PR before building on its changes; do not assume it is merged.
2. Introduce stable IDs and minimal viewer-neutral spatial records when needed, without inventing building-level detail prematurely.
3. Design a **versioned, read-only world-state interface** (snapshots, event deltas, region queries, simulation time, generation seed/version), with explicit consistency and access rules. No requirement to build a network server immediately.
4. Validate the contract first with a simple 2D observer/RPG; a 3D browser renderer can later consume the same data.
5. Keep optional AI orchestration and visual procedural generation separate from authoritative state transitions.

**Core principle:** Build and evolve the universe once; offer multiple ways to observe or interact with it.
