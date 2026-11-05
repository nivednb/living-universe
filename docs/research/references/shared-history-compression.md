# Shared-history compression: evidence and decision

Reviewed 2026-11-05. Literature-backed evaluation, not a claim of implementation or measured Living Universe savings.

## References

- Nevill-Manning & Witten (1997), SEQUITUR, hierarchical grammar induction on repetitive symbol sequences: https://doi.org/10.1093/comjnl/40.2_and_3.103
- Grammar-compressed sequences with rank/select support (2017): https://www.sciencedirect.com/science/article/pii/S157086671630034X — strong compression on selected repetitive sequences; not a universal ratio.
- Maneth & Peternek (2018), Grammar-based graph compression: https://www.sciencedirect.com/science/article/pii/S0306437917301680 — repeated graph structures and some direct queries.
- Aion (EDBT 2024), temporal graph storage with time and entity indexes: https://jimwebber.org/publication/2024-edbt/
- Zstandard dictionary compression: https://facebook.github.io/zstd/ — established baseline for shared redundancy across records.
- Practical decompression tradeoff report: https://github.com/facebook/zstd/issues/4175 — workload-dependent overhead warning, not a general benchmark.
- Event-graph timeline summarization (EMNLP 2021): https://aclanthology.org/2021.emnlp-main.519/ — relevant for narrative summaries but **lossy**, not a substitute for canonical history.

## Decision

**Defer custom shared-history pattern encoding.** First implement bounded-memory storage-backed event history, consistent restart checkpoints, schema/version integrity and conventional lossless compression. Shared dictionaries, grammar-based compression and graph indexing are candidates only after measurements demonstrate their marginal benefit on actual workloads.

## Evaluation gate

Compare identical canonical event streams under: (a) compact typed events + zstd; (b) dictionary-trained zstd; (c) established grammar compressor where appropriate. Include dictionary/index overhead and CPU, write throughput, random reads, RAM, crash recovery and exact roundtrip. Do not use semantic similarity as deduplication: near-matches require complete residual information to remain lossless. Keep historical truth and character beliefs separate. No claims of compression ratio until measured.
