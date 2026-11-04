# Temporal history and epistemic access model

**Status:** Architecture specification, not an implemented simulation feature.

## Design goals
Represent a cosmologically old universe without simulating every historical day; preserve causal consistency, historical mystery and the possibility of extremely long-lived witnesses. The engine must not give every character omniscient access to world history.

## Time representation
- Use signed integer ticks for canonical simulation time, with explicit units and calendar mappings.
- Allow negative ticks for pre-start history. Avoid floating-point years as event IDs.
- Do not assume a fixed cosmological age: configurable epoch boundaries and large time horizons.
- Distinguish event occurrence time, observation time, recording time and discovery time.

## Three distinct layers
1. **World truth**: authoritative events, physical consequences and historical states.
2. **Evidence**: artifacts, geological strata, archives, observations and testimonies with provenance and preservation conditions.
3. **Belief**: agent- and institution-specific claims, confidence, memory, access permissions, deception and transmission histories.

No belief automatically changes world truth. A correct belief may have weak evidence; an incorrect belief may be widespread.

## Historical resolution
- Cosmological epoch: coarse generative constraints and rare anchor events.
- Geological epoch: terrain, resources, biomes, extinctions and surviving artifacts.
- Ancient civilization epoch: institutions, migrations, technologies, lineages, wars, lost knowledge.
- Recent era: detailed agent biographies, settlement records and event chains.
- Active simulation: causal event log with deterministic checkpointing and event validation.

**Compression must preserve causally relevant facts.** A summary is not a substitute for a necessary event record. Retain immutable event IDs, causal links and selected original evidence even when indexes and renderings are aggregated.

## Long-lived witnesses
Characters can retain firsthand observations across millennia, but observation is local and memories can be incomplete, altered, forgotten or deliberately falsified. Age alone never grants universal knowledge. Preserve the distinction between a character's private memory and objectively validated event data.

## Research and legal provenance
Source fiction informs original motifs and mechanics; it is not automatically a reusable character-history database. Use public-domain or explicitly compatible sources when copying material. Track origin, license, edition/translation, transformed design and citations.

## Implementation stages
1. Typed historical events, evidence and claims with deterministic IDs.
2. Epistemic access tests: unobserved events remain unknown, rumors do not become truth.
3. Historical seed generator with configurable epochs and causal validation.
4. Versioned storage and replay; selective event retention and archival.
5. Multiple independently generated starting worlds for reproducible experiments.

## Non-goals for first prototype
No physically simulated big bang, no detailed billion-year agent timeline, no perfect human-like autobiographical memory, no fully procedural 3D world.
