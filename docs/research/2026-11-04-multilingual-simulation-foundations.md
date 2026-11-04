# Multilingual research round 1 — simulation foundations (2026-11-04)

Status: **discovery only**. No source code or assets imported, and no performance claims independently reproduced.

## Findings

| Candidate | Role | Evidence | Licensing and integration gate |
| --- | --- | --- | --- |
| [krABMaga](https://github.com/krabmaga/krabmaga) | Rust discrete-event agent-based simulation kernel | Separation of visualization and simulation; example models | Repository identifies MIT license. Benchmark 100/1k/10k agents, persistence and deterministic replay. |
| [AstraWeave](https://lazyxeon.github.io/AstraWeave/) | Rust AI-native ECS/planning architecture | Claims deterministic, tool-validated simulation and 12,700+ agents at 60 FPS | Documentation identifies MIT; independently inspect code, benchmark conditions, dependencies and maintenance before adoption. |
| [Cultivation World Simulator / 修仙世界模拟器](https://github.com/4thfever/cultivation-world-simulator) | Cultivation, sects, long-duration actions, agent decisions and observer mechanics | Chinese README documents spiritual energy, sects, character memory, actions spanning months, rules plus LLM | **License unresolved pending direct file-level verification**; third-party license classifiers disagree. Treat as reference-only until verified; do not import. |
| [HASH Engine](https://simulation.hash.ai/platform/engine) | Rust simulation engine with Python/JS model support | Vendor describes self-hosted simulation with millions of agents | Vendor scale claim unverified; check current source, license, active maintenance and API. |
| [MelonS Agents / PawnSim](https://github.com/MelonS/MelonS-Agents) | Automated UI-level tests and unattended simulation soak tests | Korean/English documentation of game verification and attribution practices | Inspect licenses and separate game from automation pipeline. |

## Key architecture conclusion

Five countries do not require five fully detailed continuous simulations. Maintain one global event queue and authoritative world state; apply detailed spatial and behavioral updates selectively while ensuring all consequential remote events continue. Preserve each individual's identity, knowledge, history and causal consequences.

## Next experiments

1. Run a small reproducible agent-scheduling benchmark with fixed seeds, varying 100, 1,000, and 10,000 agents.
2. Compare Rust simulation engines against a minimal purpose-built event scheduler for integration complexity and speed.
3. Define event schema, agent identity, world field sampling and cross-tradition perception contracts.
4. Run a Chinese-language code-level audit of cultivation simulator long actions, memory and rule validation without importing restricted code.
5. Test unattended multi-century progression for consistency, event volume and storage requirements.

## Research rules

Search multilingual sources (Chinese, Japanese, Korean, Spanish, German, French, Russian and others) by technical concept, not English translation alone. Track upstream source, exact revision, author, license, documentation, activity, integration fit and benchmark evidence. Commercial reuse of our original project is permitted as a goal; exclude incompatible source and assets from the redistributable core.
