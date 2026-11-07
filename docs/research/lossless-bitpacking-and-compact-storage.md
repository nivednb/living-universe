# Lossless compact representation research — bit-level storage

**Status:** Research proposal; not implemented or benchmarked.  
**Related:** ADR-0009 (single SQLite transactional authority).  
**Scope:** Physical encoding only. No simulation rules, epistemic boundaries, or authority changes.

## Findings

A storage representation has no universal minimum word width. Python uses dynamically sized integers and objects; current checkpoints are textual JSON; SQLite uses variable-length record encodings, with signed 64-bit INTEGER values where applicable. Domain integers beyond SQLite's signed 64-bit range must retain an exact compatible representation (ADR-0009 proposes canonical decimal TEXT). A 2-, 4-, or 6-bit field is feasible *when the value domain is bounded*, but SQLite does not expose native sub-byte column types: multiple fields must be packed into BLOBs or encoded into larger integers. Bit packing is not equivalent to changing the implementation language.

For a field with N possible values, fixed-width encoding needs ceil(log2 N) bits. Examples: boolean 1 bit; 4 states 2 bits; 16 states 4 bits; 64 states 6 bits. A hypothetical 1+2+3+4+6-bit group occupies 16 bits before record keys, schema, optionality, indexes and framing. Values must have explicit semantics and versioned encodings; new states can exceed the reserved width. Missing/unknown/nullable values may require extra codes or a presence bitmap.

**Information-theoretic constraint:** arbitrary event IDs, unbounded counters, text, dynamic relationships and lossless historical evidence cannot be universally represented by a fixed handful of bits. Encoding must preserve distinguishability and reconstructability. A short code may refer to a dictionary entry but the dictionary and its evolution also consume space.

## Candidate techniques

| Technique | Suitable data | Risks and requirements |
| --- | --- | --- |
| Bitsets / packed enums | Alive flags, bounded status fields, categorical powers | Versioned codebook, missing values, random update amplification, cross-byte bit ordering |
| Variable-length integers (varint / zigzag) | Small nonnegative or signed numeric values | Arbitrary-precision support, exact decode limits, canonical encodings, signed years |
| Delta encoding | Monotone event ordinals, commit IDs, sorted keys | Resets and random-access checkpoints; signed deltas; no loss of original order |
| Dictionary encoding | Repeated names, event kinds, technique IDs, region strings | Dictionary versioning, reference integrity, rare/novel values and locality |
| Columnar packing / run-length encoding | Large homogeneous agent-state batches, repeated flags | Hot-row update costs, sparse mutations, query and index complexity |
| Lossless block compression (zlib baseline) | Cold history and complete snapshot payloads | Random-access block sizing, expansion caps, checksums, CPU and temporary memory |
| State after-image/delta storage | Changed rows per committed transition | Completeness proofs, tombstones, provenance, exact historical reconstruction |

Prefer measuring total bytes (payload + dictionaries + indexes + revisions + WAL + backup) rather than raw bits per field. Bit packing can *increase* total costs if it forces full BLOB rewrites or prevents useful indexing.

## Benchmark proposal (future, isolated)

Use the same canonical deterministic workload and exact snapshot as baseline. Compare: canonical JSON; zlib-compressed JSON; canonical varint/zigzag encodings; packed categorical BLOBs; dictionary-encoded strings; and combined approaches. Record raw and compressed bytes, SQLite main/WAL/SHM files, indexes, revisions, backup size, write amplification, encode/decode CPU, point lookup, paged read, restore time, and Python/native RSS. Include 1k, 10k, and 100k agents and skewed vs high-entropy attributes. Do not extrapolate million-agent performance from small fixtures.

**Mandatory correctness gates:** round-trip byte/semantic equality as appropriate, exact existing world snapshot/digest, stable insertion and event order, signed years, large integers, witness/claim boundaries, unknown values, dictionary migration, truncated/corrupted input, adversarial decompression sizes, transaction rollback and version rejection. Use an explicit encoding version and endian/bit-order specification. Never silently truncate or saturate values. Preserve original source checkpoints.

## Recommended sequencing

1. Complete ADR-0009 Phase 1 copy-only transactional snapshot-envelope correctness and crash tests unchanged.
2. In a separate experimental branch, benchmark lossless physical encodings on representative snapshots and event/knowledge data.
3. Adopt only measured wins after the normalized shadow representation has proven capture completeness; retain a compatible decoder and reversible copy migration.
4. Revisit packed layouts when entity access patterns, hot/cold splits, and historical observation workloads are known.

**Decision:** investigate sub-byte encodings seriously, but do not impose 2/4/6-bit widths globally or treat this research as authorization to change authoritative persistence.
