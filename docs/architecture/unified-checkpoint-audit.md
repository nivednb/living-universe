# Unified kernel checkpoint audit

The initial audit dated 2026-11-04 was superseded by the
[foundation stability report](foundation-stability.md). The original 55 tests
were independently run under Python 3.12; all passed. Additional regression and
fault-injection tests now cover previously untested defects.

Unified checkpoints include clock, RNG, sequence, pending actions, routes, border
history, character registries, residency/transit, destiny, techniques, discovery
sources, historical events/claims/witnesses, memories, world claims and beliefs.
Snapshots and saves use the same encoding as the canonical digest.

Schema version and simulation rules version are separate gates. Rules version 2
fixes research completion after teaching; version 1 is rejected without automatic
migration. See the stability report for the exact contract and limitations.
