# Lossless storage research and design candidates

This document is an investigation, **not** an implemented persistence subsystem. See [research references](references/long-horizon-storage.md).

## Candidate architecture

1. Authoritative typed state: numeric IDs, normalized tables, shared immutable definitions; avoid repeating strings or serialized Python object graphs.
2. Compact event records: versioned event type ID, time delta, actor/target IDs and typed payload; dictionary/varint/delta/bit packing where applicable. Preserve original semantics, ordering and RNG state.
3. Periodic consistent checkpoints: persist authoritative state, event cursor, pending queue, RNG, rules version and schema version. Exact replay requires the matching code, inputs and environment assumptions.
4. Storage-backed archive: SQLite for current state and query indexes; append-only immutable segments with Zstandard for older events; Parquet as a benchmark candidate for analytical columns, not automatically the primary transactional store.
5. Optional content-addressed chunks: hash and deduplicate identical immutable blocks; measure overhead and avoid assuming identical semantic content has identical bytes.
6. Lazy presentation: deterministic decode to structured records, then optional AI-generated prose. AI prose is never authoritative; store provenance and label uncertain interpretations.

## What 'lossless' means

- **Bit-exact:** decoding recovers original bytes, including any details not understood by the application.
- **State-exact:** canonical authoritative state and future simulation continuation match, but discarded intermediate event history may not be recoverable.
- **Narrative-equivalent:** descriptions seem similar; **not** acceptable as lossless storage.

No universal algorithm compresses every input. A generator/seed can replace a large output only when it is actually reproducible from the preserved program, inputs, versions and random stream. Generating an alternative plausible past is not recovering the actual past.

## Proposed measurements

Compare canonical JSON, compressed JSON (zstd), typed binary event logs, SQLite and columnar archive exports on identical workloads. Measure disk bytes/event, live RSS, write throughput, random historical queries, full and partial restore, CPU cost, checksum verification, crash recovery and cross-version replay. Record both warm and cold access costs. Do not replace rules-v2 persistence until an independent roundtrip and deterministic-equivalence suite passes.
