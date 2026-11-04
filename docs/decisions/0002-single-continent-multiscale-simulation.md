# ADR-0002: One continent with five autonomous regions

**Status:** Accepted as the implementation default (2026-11-04); geographic details remain configurable.

## Decision
Preserve five culturally distinct starting civilizations—magic, cultivation/immortality, science, primal and inborn superpowers—plus a neutral central meeting region. Implement them on one large connected landmass with forests, mountains, wilderness, rivers and traversable corridors between regions. Regions may function politically as independent countries; visual geographic scale is independent of political simulation scale. Later oceans, islands, realms and remote territories remain possible.

## Why
Avoid requiring six separate always-loaded high-resolution maps or complicated inter-island navigation. Preserve travel, migration, trade, conflict and cultural exchange without constraining agent learning by birthplace.

## Simulation strategy
- Global layer: coarse geography, fields, population, institutions, trade, travel and major events.
- Regional layer: settlements, transport, ecology, resources and strategic changes.
- Local layer: detailed 2D tiles, buildings, active interactions, combat and damage when necessary.
- Individual identities persist globally. Inactive agents use scheduled events and compact state, not continuously running high-frequency AI.
- Observer proximity affects rendering and detail, **not** whether consequential events occur.
- Spatial field values use sparse or multiresolution representations; only active areas need high-resolution updates.
- Record causal events, deterministic seeds and snapshots; test replay integrity.

## Performance policy
10,000 NPCs is a design target, not a measured capacity claim. Benchmark with reproducible scenarios at 100, 1,000 and 10,000 agents. Measure simulation time per world-day, memory, database growth, event throughput and optional AI usage. Use batch/event-driven decisions and budget expensive AI selectively. Do not assume geographic size alone predicts runtime cost.

## Expansion
World coordinates and stable region IDs must not require migrations when expanding the visible map. New settlements, distant territories, additional realms and deeper detail may be added without changing the original five-civilization concept.

## Licensing
Original reusable project components should permit commercial and noncommercial downstream use. Third-party components must be compatible with their actual licenses; do not import noncommercial material into the redistributable core.
