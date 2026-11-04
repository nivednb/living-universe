# Historical seeding and cultural inheritance

**Status:** Design proposal; no historical dataset imported yet.

## Principle
Every civilization begins with meaningful inherited history, but no scripted destiny. Ground-truth world history, surviving records, local beliefs, mythology, propaganda and secrets are distinct data layers.

## Source-informed starting cultures
- **Science:** draw on documented human history of technology, institutions, agriculture, medicine, migration, science and economic organization. Transform it into a fictional chronology; do not presume an exact replay of Earth.
- **Primal:** draw on archaeology, anthropology, ecology and public-domain myth alongside original prehistoric fantasy. Avoid portraying living Indigenous cultures as primitive or static.
- **Cultivation/immortality:** study broad xianxia/xuanhuan conventions, Daoist historical concepts with appropriate cultural context, public-domain literature and legally usable references. Invent original sects, techniques, eras, conflicts and philosophies.
- **Magic:** compare global folklore, mythology, historical magical traditions and genre mechanics; build original institutions, epistemology and spell systems.
- **Inborn superpowers:** compare general mutation, inheritance, giftedness, institutions and hero-fiction conventions; create original lineages, abilities, ethical conflicts and power constraints.
- **Central nexus:** independently evolved crossroads of migration, diplomacy, trade, research and mixed traditions.

## Data model
- HistoricalEvent: id, time interval, place, actors, consequences, evidence, provenance, confidence.
- Character: identity, age, relationships, physiology, skills, knowledge, beliefs, goals, inventory, commitments, memory references.
- KnowledgeClaim: proposition, evidence, confidence, discoverer, transmission path, secrecy, falsifiability.
- CulturalInstitution: founding event, membership, doctrine, assets, internal politics, historical changes.
- WorldTruth: versioned laws, objective events, resources, field states and physical consequences.

## Initialization process
1. Create an original fictional timeline and initial state from licensed/public-domain and factual research.
2. Populate representative institutions, settlements, generations, knowledge traditions and conflicts.
3. Generate character-specific memories consistent with the fictional historical event graph.
4. Validate contradictions, provenance, resource conservation and relationship consistency.
5. Start autonomous simulation from the seeded state. All subsequent history arises from simulated events.

Historical seeds should be reproducible, optional and editable for experimental worlds. No claim that any fictional character or event is taken from a protected franchise.
