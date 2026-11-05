# Research references — lossless long-horizon simulation storage

Reviewed 2026-11-05. These are external sources, not original Living Universe findings. Links are pointers to original publications and specifications; respect their licenses.

## Cosmological and long-horizon simulation

- Illustris data model and snapshots: https://www.illustris-project.org/data/docs/background/ — selected time snapshots, catalogs and merger trees rather than every step. Compare its fidelity constraints to our event simulation.
- REBOUND Simulation Archive: https://academic.oup.com/mnras/article/467/2/2377/2961801 — long-running deterministic orbital restart and reconstruction. Reproducibility depends on algorithm and environment, not simply seed.
- Adaptive mesh refinement overview (FLASH): https://flash.rochester.edu/site/flashcode/user_support/flash_ug_devel/node60.html — variable spatial resolution; analogy for hierarchical agent/time resolution, not a drop-in engine.

## Event histories, timelines and replay

- Microsoft Event Sourcing pattern: https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing — immutable event streams, snapshots, replay, versioning, ordering and their tradeoffs.
- Martin Fowler, Bitemporal History: https://martinfowler.com/articles/bitemporal-history.html — when an event occurred versus when it was recorded or learned.
- SQLite write-ahead logging: https://www.sqlite.org/wal.html — transactional disk-backed current state and append-oriented operations; operational and durability constraints apply.

## Compact exact representations

- Apache Parquet encodings: https://parquet.apache.org/docs/file-format/data-pages/encodings/ — dictionary, run-length, bit-packing and delta encoding for typed columns.
- Apache Arrow columnar format: https://arrow.apache.org/docs/format/Columnar.html — typed buffers, dictionary and run-end encoding for efficient in-memory representation.
- Protocol Buffers encoding guide: https://protobuf.dev/programming-guides/encoding/ — typed binary fields, varints and packed repeated fields; schemas are necessary to decode.
- Zstandard: https://facebook.github.io/zstd/ — general-purpose lossless compression, including dictionary-trained approaches for small repetitive records.
- Content-addressed Merkle DAGs (IPFS): https://docs.ipfs.tech/concepts/merkle-dag/ — immutable content identification, deduplication and shared structure; does not itself compress arbitrary information.

## Relevant adjacent work

- Continuous Simulation Data Stream: https://infoscience.epfl.ch/entities/publication/c90a72ee-d4fb-4c2a-b6b5-5a115c157bb2 — individual object output schedules; verify applicability before adopting reported savings.
- Dynamic Hierarchical Agent Compression: https://doi.org/10.4018/978-1-4666-1830-5.ch018 — hierarchical agent representations; investigate assumptions and availability of full text before relying on performance claims.

## Interpretation

A binary format is not inherently more compressed merely because it is closer to machine language. Exact recovery requires enough encoded bits plus schema, decoder, versions and any shared dictionaries. Text generation by an LLM is a presentation layer, not a lossless decoder. Keep machine-readable canonical state separate from human-readable narrative. Any claimed losslessness must be tested with byte-level or canonical-state roundtrips and deterministic continuation.
