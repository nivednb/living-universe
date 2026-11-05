# Foundation stability report — 2026-11-05

Baseline: `2872624c1a5b109b311704d7db4d1a1ffae7f98c`. No gameplay systems or
external dependencies were introduced. Python 3.12.14 was used locally.

## Verification and fixes

All 55 baseline tests passed independently using the existing CI command. The
latest baseline GitHub Actions run also reported success (run `41841067134`).
The expanded suite contains 74 tests, including multi-case corruption checks.
Run it from `prototype/` with `python -m unittest discover -s tests -v`.
CI now checks Python 3.12 and 3.13; the rules-v2 golden digest detects divergence
between supported runtimes. Local execution of Python 3.13 was not available.

Four targeted regression tests were also run against the original implementation:
three failed assertions and one errored. They reproduce successful rediscovery
after teaching, boolean durations, fractional route times and overwriting an
abandoned fixed-name temporary file. All pass with these changes.

The implementation now:

- Rejects malformed checkpoint fields, row shapes, non-integer clocks/IDs,
  duplicate IDs and set members, noncanonical actor map keys, duplicate JSON
  keys, non-finite JSON numbers and invalid RNG state before reconstruction.
- Checks actor registries, one residence or transit per actor, region agreement,
  destination existence, exactly one arrival per traveler, research prerequisites,
  event sequence uniqueness, heap ordering and the derived research queue index.
- Checks discovery sources against registered prerequisites and current knowledge,
  duplicate discovery provenance, outcome references and successful rolls.
- Checks historical witnesses, witness memories, claims, evidence references and
  beliefs. Direct event knowledge requires witnessing; communicated claims remain
  distinct from directly witnessed history. Claim/event identifiers cannot collide.
- Checks resources, route attributes, border history and bounded character data.
- Validates live snapshots/saves through the same domain invariant checker used
  by restores, without drawing randomness or changing world state.
- Uses a unique sibling temporary file, flushes and fsyncs it, then atomically
  replaces the checkpoint. Failed writes, fsync and replace preserve the previous
  checkpoint and clean up that attempt's temporary file.

Tests include simultaneous arrival/research ordering, teaching during research,
successful provenance (without conditional assertions), claims and beliefs across
restore, several corrupt-state matrices, truncated JSON, injected partial writes,
fsync/replace failures and an actual subprocess exit just before replacement.
A hard process exit leaves an unused temporary file, which future loads ignore.
Three seeds run 100 rounds with periodic restores and invariant checks. Separate
processes also verify independence from Python hash randomization.

## Architecture and compatibility

`unified_kernel.py` owns mutation, clock and queue. Domain models in `borders.py`,
`discovery.py`, `history.py` and `world_state.py` remain usable standalone.
`checkpoint_schema.py` validates serialized structure before lossy reconstruction;
`invariants.py` validates the reconstructed domain and can audit a live kernel.
`unified_persistence.py` owns encoding and filesystem operations.

Schema version remains **1**; simulation rules version is now **2**. Completion
of research whose target was taught in the meantime consumes its scheduled RNG
draw and records an unsuccessful research outcome, without adding a discovery.
This preserves the random stream while preventing duplicate provenance. Generated
history IDs also avoid seeded event/claim collisions. These behavioral changes
require the rules bump. Rules-v1 checkpoints are rejected explicitly, even when
their particular state would not exercise the defect. There is no silent migration.

The pending-research actor set is a derived index, rebuilt from the queue on load
and checked by invariants. It removes the linear queue scan from every research
request without changing encoded state or queue order. The heap remains ordered
by `(day, sequence)`; equal-day jobs execute in scheduling order. Different command
orders intentionally produce different histories and RNG draw assignments.

Integrated checkpoints require registered techniques for character knowledge and
registered actors/events/claims for referenced knowledge. Seed imported history
with negative years if needed; future events are not historical facts. Techniques
may be registered in any order during setup, but all prerequisites must exist by
the first snapshot. Standalone model knowledge labels are less constrained.

## Benchmarks

Reproduce from `prototype/`:

```sh
python benchmark_unified.py --agents 100 --rounds 100
python benchmark_unified.py --agents 1000 --rounds 100
python benchmark_unified.py --agents 5000 --rounds 20
```

Linux x86_64, Python 3.12.14, seed 42, rules 2. Single container observations,
not statistically controlled capacity measurements. Each round advances 10 days,
schedules one journey and one research job per actor and registers a new shared
technique. Setup is timed separately. Simulation timing includes scheduling,
completions and history recording, but excludes final validation/checkpoint work.

| Actors | Days | Scheduled events | History entries | Simulation seconds | Events/s | Save/load seconds | Peak RSS MiB |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 1,000 | 20,000 | 40,000 | 0.150 | 133,070 | 0.159 / 0.118 | 75.1 |
| 1,000 | 1,000 | 200,000 | 400,000 | 2.688 | 74,401 | 2.177 / 1.930 | 680.4 |
| 5,000 | 200 | 200,000 | 400,000 | 3.092 | 64,682 | 2.663 / 2.236 | 706.5 |

Every run compares its final digest with a second run that saves/restores during
travel and research, and advances in different chunks. All matched. Checkpoints
at the midpoint occupied 1.90, 19.79 and 21.52 MB respectively. Peak RSS covers
the entire benchmark process, including JSON encoding/loading and continuation;
it is not just steady-state simulation memory. Raw observations are recorded in
[`../benchmarks/foundation-2026-11-05.json`](../benchmarks/foundation-2026-11-05.json).

Before adding the research index, the same 1,000-actor workload took 7.955 seconds
and the 5,000-actor workload took 35.650 seconds. After the index they took 2.688
and 3.092 seconds, with identical digests. These single-run comparisons indicate
the removed quadratic scheduling cost; they are not precise speedup guarantees.

## Remaining limits

- All histories, knowledge and outcomes stay in memory indefinitely. Snapshot
  normalization creates additional full JSON representations. History compaction,
  streaming checkpoints and storage-backed history need separate design work.
- Files are consistency-checked, not authenticated. There is no checksum capable
  of detecting every valid-looking edit, hostile-input size/depth limit or sandbox
  for arbitrary untrusted checkpoints. Use trusted, reasonably sized files.
- Saves provide process-interruption atomicity on a local filesystem. Directory
  metadata is not fsynced, so power-loss durability is not guaranteed. There is no
  multi-writer ordering policy; the last successful replacement wins. Serialize
  kernel mutation while saving. Hard-kill temporary files need manual cleanup.
- Snapshots retain registry insertion order in arrays. Reproducibility assumes
  the same seed, rules, setup/command order and supported Python runtime. This is
  not a cross-language replay specification or a hash of equivalent unordered worlds.
- Hidden destiny, RNG and world facts are present in authoritative checkpoints;
  checkpoints are not safe character-facing or untrusted-client views. Teaching
  has no proximity constraint, and research during transit remains permitted.
- Legacy experiments and their save formats remain separate. No autonomy,
  ecology, institutional simulation, renderer or production server is implied.
- No external code/assets or paid services were added. The repository still lacks
  an explicit source-code license; owner selection is needed before code reuse
  has clear open-source licensing terms. `LICENSE-DOCS` applies to documentation.
