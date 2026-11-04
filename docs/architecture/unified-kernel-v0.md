# Unified event kernel v0

`prototype/unified_kernel.py` is the first standalone vertical slice integrating:
- one simulation clock and deterministic priority queue;
- scheduled travel with settlement membership updates;
- scheduled interdisciplinary research with seeded chance;
- per-actor hidden destiny modifier (bounded and never guaranteed);
- teaching and history events with restricted witness access;
- canonical snapshot digest for reproducibility testing.

This is **not yet** the production authoritative kernel. It does not integrate `prototype/sim.py` or `prototype/persistence.py`, and cannot yet save/restore. No autonomous agent planning, institutions, fate propagation, planetary powers or full historical generation are implemented. Research can occur during travel in this simplified model. The event log currently records descriptions rather than a durable typed event schema.

Destiny is presently a fixed per-actor modifier, not a comprehensive cosmic field. Luck is a seeded random draw for research completion. Future versions should add environmental, relational and temporal influences while preserving reproducible replay. The current snapshot does not yet include every setup parameter (e.g. routes), so its digest is for comparison of otherwise identical worlds, not a complete persistence format.

Run tests from `prototype/`: `python -m unittest discover -s tests -v`.
