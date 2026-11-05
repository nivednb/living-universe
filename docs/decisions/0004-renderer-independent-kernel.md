# ADR-0004: Renderer-independent simulation and benchmark-first selection

**Status:** Accepted 2026-11-04.

The world is an authoritative graph of entities, relationships, events and multiscale spatial fields; no continuous rendering or 3D physics is required for existence. 2D and future 3D clients consume projections of the same state.

**Immediate implementation:** a minimal Python-standard-library reference scheduler in `prototype/`, with reproducibility tests. It is intentionally not the production runtime.

**Production candidates:** compare krABMaga (MIT, discrete-event ABM), NeXosim (MIT/Apache-2.0, discrete-event, save/restore), and Bevy ECS (MIT/Apache-2.0, data-oriented entities) with a custom Rust scheduler. Godot and Cocos are candidates for a later renderer, not the source of simulation truth.

**Selection gates:** deterministic replay across process restarts, state schema/version migration, 10k-agent benchmark, realistic event load, stable identities, field queries, cross-cultural mechanics, operational simplicity, security, license compatibility, and low hosting cost. Do not pick by synthetic agent-count claims alone.

Sources:
- https://github.com/krABMaga/krABMaga
- https://github.com/asynchronics/nexosim
- https://docs.rs/bevy/latest/bevy/ecs/
- https://godotengine.org/license/
- https://github.com/cocos/cocos-engine

Progress: the Python unified kernel now supports validated checkpoint restoration,
historical provenance and detached observer/character views. The [view contract](../architecture/view-contract.md)
defines the current region/route graph and the boundary for future 3D support.

Next: typed causal event schemas, authoritative spatial queries and fields, and a
Rust benchmark under matching semantics. Spatial mechanics need explicit units,
precision and deterministic behavior before selecting renderer physics. Avoid
LLM calls in per-agent simulation loops.
