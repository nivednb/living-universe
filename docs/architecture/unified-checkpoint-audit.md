# Unified kernel checkpoint audit (2026-11-04)

**Status:** Implementation and tests committed; independent test execution not verified.

## Implemented
- Versioned JSON checkpoint, atomic file replacement, no pickle/eval.
- RNG state, event queue order/sequence, day, actor and destiny data.
- Settlements and resources, residence, in-transit destinations, routes and border history.
- Techniques, expertise, knowledge, discovery records, historical events, claims, witnesses, beliefs and outcomes.
- Restoration invariants for agent registry consistency, residency, transit, pending-event time and event sequence.
- Canonical digest now uses the complete checkpoint state rather than a partial view.
- Five checkpoint tests cover in-flight travel plus pending research, deterministic continuation, RNG restoration, corrupt residency, unsupported versions and invalid event timing (six scenarios across five methods).

## Known limitations and next hardening
- The main legacy `sim.py` remains separate; no automatic migration of its checkpoint format.
- Tests were committed but not executed in this environment. GitHub Actions should be checked before declaring a passing build.
- The loader does not yet exhaustively validate every field/type or defend against maliciously large JSON; treat checkpoints as trusted inputs.
- Engine rule version is not yet pinned separately from checkpoint schema.
- Research during transit is currently permitted by design of this prototype.
- Luck currently applies only to research; broader fate fields and autonomous decisions remain future work.
- Need fault injection, property-based invariants, load/save cross-version tests, deterministic replay and benchmark tests before treating this as production-grade.

Run: `cd prototype && python -m unittest discover -s tests -v`.
