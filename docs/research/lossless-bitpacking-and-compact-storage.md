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


## Verified external implementations (source review, November 2026)

These are **implemented mechanisms in other software**, not benchmark results for Living Universe.

1. **SQLite record format**: SQLite documents serial-type encodings with integer payload widths of 1, 2, 3, 4, 6 or 8 bytes; integer 0 and 1 may take zero body bytes. This already avoids fixed 64-bit payloads for many small numbers, though rows, pages, headers and indexes have additional overhead. Source: https://www.sqlite.org/fileformat2.html
2. **Apache Parquet**: its maintained format specification includes a hybrid run-length/bit-packing encoding, bit-packed booleans, dictionary-coded values, delta binary packing and delta byte arrays. Dictionary indices use an explicit bit width; the specification's example of 30 two-bit values occupies 60 data bits, rounded to 8 bytes, excluding framing. Its standalone older BIT_PACKED encoding is deprecated in favor of the RLE hybrid. This directly verifies practical sub-byte packing. Source: https://parquet.apache.org/docs/file-format/data-pages/encodings/ ; implementation matrix: https://parquet.apache.org/docs/file-format/implementationstatus/
3. **Zstandard**: the reference implementation provides lossless compression and dictionary training. Its published Silesia benchmark (i7-9700K) reports zstd 1.5.7 level 1 at 2.896x, 510 MB/s compression and 1550 MB/s decompression, versus zlib 1.3.1 level 1 at 2.743x, 105 MB/s and 390 MB/s on that corpus. These figures are hardware/corpus-specific and not transferable to our event stream. Source: https://github.com/facebook/zstd

### Consequences for Living Universe

**Verified feasible:** 1–6-bit categorical packing, mixed RLE/bit-packed streams, delta and dictionary encoding, variable-width small integers, and lossless compressed history blocks are established production techniques. We need not invent these algorithms.

**Not yet verified for this workload:** whether packed BLOBs beat normalized SQLite columns on total file/WAL/index size and update cost; whether Zstandard beats zlib on our event/knowledge distribution after dictionary overhead; whether random historical reads remain fast; whether an integrated layout keeps exact provenance, versioning and crash recovery.

**Selection guidance:** retain SQLite as transactional authority; first try its native compact encodings. For dense cold categorical columns, prototype the Parquet-style RLE/bit-packing technique in an independently versioned payload, without requiring Parquet as the live database. Compare zlib and zstd on bounded independently decompressible blocks. Do not add Parquet/RocksDB as additional authoritative stores merely for compression. Never interpret an external benchmark as an achieved Living Universe saving.

**Follow-up experimental gate:** record field cardinalities and frequency distributions on real/synthetic world snapshots; compare SQLite native schema vs packed BLOB vs dictionary/RLE on identical events, claims, witness grants and updates, including WAL/checkpoint costs. Require exact round-trip and corruption tests before adoption.
