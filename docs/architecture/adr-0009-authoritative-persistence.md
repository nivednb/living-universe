# ADR-0009 — A single SQLite transactional authority, with versioned state revisions

**Status:** Proposed, for architecture review. **Not implemented or accepted.**
Date: 2026-11-05. No simulation rules, kernel mechanics or viewer implementation
are changed by this ADR. The accompanying temporary-database probe is evidence,
not a persistence adapter, migration, or replacement ledger.

## 1. Decision and verified starting point

Recommend **one SQLite database per universe as the only commit authority** for
current state, history, epistemic state, RNG, pending actions and command receipts.
Use WAL, one serialized writer, short read transactions and explicit version gates.
Persist complete row after-images/tombstones alongside current-row updates in the
**same transaction** once capture completeness is proved. These revisions support
historical state at committed boundaries; human-readable history is not the redo log.
Snapshots, compressed exports and external archives are initially disposable read
accelerators or independently verified backups, never a second commit authority.
Row revisions are storage versioning inside that one SQL transaction, not a
separately committed gameplay journal. Current projections and revisions must
agree; disagreement is corruption, not permission to choose whichever copy is
more convenient.

This is the simplest next design that removes the existing SQLite/JSON atomicity
gap without requiring a new causal event language or an external-file manifest.
It is not a promise that SQLite or the current Python kernel will handle a million
active agents at any particular speed. Revisit the decision when one-writer I/O,
revision growth, backup size, or observation latency fails measured gates (§7).

The branch relationships were verified through actual PR/commit metadata:

| Reference | Exact head | Relationship / status |
| --- | --- | --- |
| `main` | `2872624c1a5b109b311704d7db4d1a1ffae7f98c` | Default branch |
| PR1, `codex/stabilize-foundation` | `a1b455006d489dd7275aff47fcbe2b498aae139d` | Unmerged; base is main |
| PR3, `feature/sqlite-history-ledger` | `4a52afedcb00693777cd3bb4fa2e1d9574e34b1e` | Unmerged; base is foundation |
| PR4, `codex/viewer-independent-projections` | `523e7e1bcbf8854132ae60b44307475069291cb4` | Unmerged; base is foundation |

PR3 and PR4 are siblings, not prerequisites of each other. This documentation
branch starts from **exactly the foundation head**, not from either sibling.
References below are pinned because the audit and view documents are not present
in that foundation tree:

- [Integration audit at PR3 head](https://github.com/nivednb/living-universe/blob/4a52afedcb00693777cd3bb4fa2e1d9574e34b1e/docs/audits/integration-audit-2026-11-05.md).
- [Current archive/publication code](https://github.com/nivednb/living-universe/blob/4a52afedcb00693777cd3bb4fa2e1d9574e34b1e/prototype/checkpoint_publication.py).
- [Viewer contract at PR4 head](https://github.com/nivednb/living-universe/blob/523e7e1bcbf8854132ae60b44307475069291cb4/docs/architecture/view-contract.md).
- [Temporal observation design](https://github.com/nivednb/living-universe/blob/4a52afedcb00693777cd3bb4fa2e1d9574e34b1e/docs/architecture/temporal-observation-windows.md).
- Current [kernel](../../prototype/unified_kernel.py), [JSON codec](../../prototype/unified_persistence.py),
  [invariants](../../prototype/invariants.py), and [renderer-independent ADR](../decisions/0004-renderer-independent-kernel.md).

The audit established per-event archive atomicity and fail-closed mismatches,
not authoritative recovery across every simulation mutation. Current JSON state
contains complete history and knowledge. Current history descriptions do not
contain every resource change, pending action, RNG state or failed travel outcome.
The probe and audit do not justify replacing the in-memory ledger now.

## 2. Alternatives evaluated

| Dimension | 1. SQLite authority + atomic revisions — recommended | 2. Authoritative append-only event journal | 3. Transactional manifest + immutable segments |
| --- | --- | --- | --- |
| Crash consistency | One transaction contains all authoritative changes; WAL recovery chooses committed transactions [S1–S3]. | Requires framed/checksummed records, durable commit markers, tail rules and either complete mutations or exact replay inputs. Materialized state is a rebuildable projection. | Segments must be written, synced, sealed and directory-synced **before** committing their references; orphan/missing-segment policy is mandatory. |
| Reproducibility | Save exact post-state RNG/queue and deterministic row order; do not let SQL row visitation define simulation order. | Excellent only with complete deterministic event/input semantics, pinned rule code and stable RNG behavior. Not demonstrated by current narrative events. | Needs the same deterministic contents plus stable segment identity, ordering and manifest semantics. |
| Historical reconstruction | Indexed row revisions + compatible snapshots give exact committed cuts without rerunning gameplay. | Replay from a compatible snapshot; requires all causally relevant inputs/deltas and an old-rule runtime or fully specified transitions. | Efficient immutable-range reads and snapshot catalogs, but references must cover all dependent state and knowledge. |
| Storage costs | Current rows, secondary indexes, revisions, WAL, snapshots and backups. Repeated RNG/after-images add write amplification. | Append is compact if events/deltas are compact; projections, snapshots, indexes and old replay runtimes add costs. | Segment compression and shared fork prefixes can reduce cold storage; manifests/indexes, orphan retention and multiple copies add costs. |
| Working memory | Indexed hot repositories and byte-budgeted readers are possible; current full dictionaries and JSON are **not** thereby made bounded. | Streaming journal reads; reconstruction needs working state and bounded indexes/caches. | Bounded block readers possible; compaction/reconstruction needs explicit byte and temporary-disk budgets. |
| Large populations | Single writer can batch many scheduled events within one advance; hot pages/index churn/fsync and long transactions eventually limit it. No measured population ceiling. | High sequential write potential; entity updates, joins and knowledge filtering require substantial additional machinery. | Good cold throughput and independent readers; distributed writes still need ordering/consistency machinery. |
| Schema evolution | Explicit storage schema/codec gates; copy-and-verify migration, preserving source. Rule versions remain separate. | Immutable event versions/upcasters or old consumers; changing replay rules can invalidate historical reconstruction. | Versioned manifest, index, segment and compression formats; coordinated migrations and GC. |
| Operations | Standard library, mature backup/integrity tooling, local filesystem, one writer. | Custom durable journal, replay validation, projection rebuilds and potentially long recovery. | More filesystem/object-store lifecycle, integrity, replication, compaction and disaster-recovery operations. |
| Current compatibility | Natural fit for complete checkpoint state; row capture can be verified against the unchanged codec before cutover. | Current descriptions are insufficient; command replay is also unproved for every mutator and intermediate cut. | Recreates an external-publication boundary similar to the audit's hard cases before simpler authority is proved. |

**Reject option 2 as the next authority**, not as a future research direction.
A journal containing *complete* versioned after-images could work, but building
its atomic metadata, indexes and recovery now duplicates facilities SQLite already
provides. Current narrative events must never be relabeled as replay-complete.
Command envelopes are retained for diagnosis/testing, not treated as the sole
source of truth. Microsoft explicitly describes event sourcing's complexity and
event-versioning obligations [S7].

**Defer option 3.** It becomes attractive for multi-terabyte cold history, shared
fork prefixes or object storage. It adds a required external-file durability and
manifest protocol. Authoritative segment publication/compaction would need a new
decision and fault tests; external read caches below do not make that switch.
WAL transactions spanning attached databases are not atomic as one set [S1]: do
not split authoritative history and live state into separately attached WAL files.

## 3. Exact transaction semantics

### 3.1 What is a transition?

A transition is **one successfully completed host-admitted mutating command**
against a specified committed parent, including all of its effects and return
value. Initially preserve existing public boundaries:

- `advance(days)` commits its entire due-event loop, ordered by `(day, sequence)`,
  and its final clock update together. Do not silently make every popped job a
  separately observable commit or acknowledge a partly completed advance.
- `depart` commits supplies, residency/transit, destination, pending arrival,
  history and border history together. A *rejected* departure still appends border
  history today; it is not necessarily a no-op.
- `research` commits the pending job, sequence increment and witnessed start event.
- Completion inside advance commits consumed RNG, known technique/provenance,
  outcome and witnessed history, even when research fails or its target was taught.
- `teach` preserves today's behavior, including false/no-change results. Such a
  valid no-op may still get a durable receipt without changing the legacy digest.
- Genesis groups setup into a **valid configuration/import batch**. Individual
  setup calls can temporarily reference a technique not yet registered, so they
  are not each declared independently restorable commits.

Resource transfers, claim publication/communication, beliefs, seeded history and
every other authoritative mutator must also pass through an explicit transaction
gateway before cutover. No arbitrary dictionary editing is permitted in a managed
authority session. The original in-memory API remains available outside that mode.

Invalid commands/exceptions do not publish a transition. If the kernel mutated
its private cache before raising or SQL commit fails, discard/reload that cache;
do not continue from its half-mutated objects. Operational error logging is not a
new historical event or an excuse to consume the authoritative RNG again.

Storage commit numbers are separate from simulation days, scheduled-job sequence
and historical event ordinals. Wall time, request identity, database UUIDs and
diagnostics are metadata outside the legacy snapshot/digest and simulation RNG.

### 3.2 One-file commit protocol

Proposed writer connection: explicit transactions, `foreign_keys=ON` checked
**before** BEGIN, `journal_mode=WAL` checked, `synchronous=FULL`, bounded busy
timeout, a local filesystem with supported SQLite locking/fsync [S1–S4]. No
network filesystem or cross-host WAL writers. One serialized command executor.

1. Bind universe and authenticated command identity in the host, not a renderer.
   Validate envelope/version/size; use a durable idempotency key and hash of the
   canonical command, including arguments and expected parent.
2. `BEGIN IMMEDIATE`. Check the receipt **before running the command**. Same key
   and same request returns its committed outcome; different input with the same
   key is an error. A stale parent without a matching receipt is a conflict.
3. Verify current manifest/version and load authoritative parent state. Run the
   existing kernel operation in a private unit of work. Do not expose speculative
   RAM to viewers, other commands, caches or notifications.
4. Validate changed state and write current rows, immutable after-images/tombstones,
   appended histories/provenance, witness/direct knowledge, communicated claims,
   beliefs, RNG, pending jobs, counters and ordering metadata in this transaction.
   Required FKs and uniqueness constraints are checked, not left disabled.
5. Insert the commit envelope, effect checksum/counts and command receipt; update
   the manifest head with a parent comparison. All references point within the
   same transaction. No external checkpoint rename participates in this commit.
6. `COMMIT`. Only after success acknowledge the command and publish a detached
   view at the new committed cursor. If acknowledgement is lost, resolve the
   persistent receipt instead of applying the command/RNG draw a second time.

An I/O error during COMMIT can leave the caller uncertain. Close/reopen safely,
inspect the receipt/head, and either return the committed result or restore the
old parent before a same-key retry. Never guess that an exception means rollback.
Fatal corruption stops writes; uncertain speculative RAM is never used as authority.

The cache can temporarily lag a committed database after a process exit; rebuild
it from that committed state. Old-or-new visibility comes from SQLite, not a
second JSON publication record. SQLite's FULL synchronization still depends on
the OS/device honoring its guarantees; process-exit tests are not power-cut proof.

Initial atomic advances may be large. The host should admit bounded advances
and benchmark the worst same-day batch before promising latency. Streaming SQL
writes within a long transaction can limit Python memory but not its duration.
Splitting a public advance into durable sub-commands requires an explicit resumable
command contract and equivalence tests; it is not silently introduced here.

## 4. Proposed data model and compatibility rules

This is a schema specification, **not an installed SQL migration**. Begin with a
minimal complete-snapshot store (§11); normalize only behind a shadow-mode gate.

| Table/family | Required contents / constraints |
| --- | --- |
| `manifest` | Universe UUID, parent lineage, application/schema/codec/rules/runtime versions, committed head/hash, genesis source hash and stream counters. One database owns one universe. |
| `commits`, `receipts` | Monotonic storage commit ID, parent hash, canonical command hash, request origin/key UNIQUE, result, effect schema/hash/counts, pre/post cursor. Receipt and effects commit together. |
| `world_clock_rng` | Exact day, seed, scheduled sequence, full RNG state/version including Gaussian cache; not seed alone. Immutable revision per changed commit. |
| Actors / traveler / researcher components | Stable actor ID, region, supplies, navigation, clearance, hidden destiny and expertise. Preserve separate traveler/researcher insertion ordinals. |
| Settlements / resources / residence / transit | Settlement ID/region/order, exact integer quantities, actor location or transit/destination. Exactly one residency-or-transit state; FKs plus domain cardinality audit. |
| Routes / actor-known-routes | Directed regions, travel time/hazard/restriction, route order and each actor's route knowledge. Known route knowledge need not imply a registered traversable route. |
| Techniques / prerequisites / actor-technique grants | Technique IDs, traditions, difficulty, source prerequisites, order and actual learned knowledge. Do not add a new prerequisite requirement to teaching; today's teach behavior is preserved. |
| `pending_jobs` | Kind, actor, target and exact due day/scheduled sequence; unique sequence and research-per-actor, exact transit-arrival pairing. Indexed deterministic numeric ordering. |
| `historical_events`, `event_witnesses` | Immutable event ordinal, original string ID UNIQUE, signed year, nonnegative simulation-day index, description, witnesses and producing commit. The UNIQUE index is the ID index; avoid a separately maintained authority copy. |
| Historical claims / `known_references` | Original claim ID, event, proposition, source and order. Known references distinguish witnessed events from received claims; both persist with actor identity and acquisition commit. |
| World claims / evidence / beliefs | Original proposition, origin event and ordered raw evidence tokens; exact actor belief grants. Preserve raw tokens when namespaces overlap; do not infer a new typed meaning or global truth. |
| Border history / discoveries / outcomes | Ordered append streams with every current field, including rejected travel, sorted discovery prerequisites, success/roll/chance. Producing commit and stable ordinal. |
| `row_revisions` | `(family, record_key, commit_id)` unique; operation after-image or tombstone, insertion ordinal, codec/hash. Current table updates and their revisions are inseparable. |
| Snapshot/backup catalog | Committed cut/hash, format, provenance, byte lengths, checksums and completeness declaration. Read-cache references are not required to recover authority. |

Foreign keys cover typed relationships. The current history event/claim namespace
must stay disjoint. World claim/evidence tokens currently have different, partly
overlapping namespaces: preserve exact strings and current validation semantics,
not invented causal links. Imported history gets `producing_commit=genesis`; its
actual earlier causal transition is unknown. New causal links are recorded only
when the executing operation actually knows them, e.g. its consumed pending job.

**Number representations:** do not silently narrow Python IDs, day or pending
sequence to signed 64-bit SQLite INTEGER. Existing kernel integers can exceed it.
Use canonical decimal TEXT for domain arbitrary integers, validated before binding
(reject booleans/floats/noncanonical digits). Numeric queue order uses indexed
`(digit_count, decimal_text COLLATE BINARY)` pairs for nonnegative values, followed
by the same pair for job sequence. Signed years preserve their sign, never REAL.
Storage-owned commit IDs/ordinals may use nonnegative INTEGER with an explicit
overflow/capacity rejection and migration plan; never wrap simulation counters.

**Ordering:** preserve insertion ordinals for every dictionary serialized as an
array by `encode`, and explicit ordinals for lists. `ORDER BY id` is not a substitute
for existing setup/history order. Maps/sets use the current canonical codec rules.
Event allocation starts at historical event count and skips both existing event
and claim IDs exactly as `_record` does; it does not use SQL rowid or UUIDs.
Storage identities are globally qualified by universe/lineage; existing event ID
strings and actor IDs are not rewritten when exported to the legacy codec.

**RNG:** persist `getstate()` completely after every transition, including its
version and optional cached Gaussian value. JSON is the initial codec. A later
explicit binary codec may encode MT words/index/cache losslessly; pin byte order,
codec and runtime. Cross-language replay is not established merely by using MT19937.
Do not reseed on restart or use world RNG for storage IDs, retries, compression,
cache eviction, observers or test-command generation.

Restore pending rows in exact due-day/sequence order and rebuild the heap and
derived `_pending_research` index without rescheduling jobs or allocating IDs.
Preserve references to still-unknown truth: a heard claim does not grant access to
its actual event or evidence. Historical knowledge and discovery provenance are
not recreated by heuristically scanning event descriptions.
Imported initial technique knowledge is tagged as imported/unknown origin, not
retroactively attributed to a teacher or discovery. Preserve every existing
`Discovery.source_knowledge` tuple exactly; new grants may reference the executing
command/commit only when that source is actually known. Acquisition cut controls
visibility, independently of the historical year described by an event.

**Versions:** rules remain 2, legacy checkpoint schema remains 1, existing view
schema remains 1. Proposed storage schema/row codec/revision codec have independent
versions. New stores have a checked application ID and explicit schema version.
Unknown, mixed, or missing versions fail before writes; no startup DDL that
silently repairs a nonempty archive. Migrations are explicit copy/verify/switch
operations with retained sources and a pinned compatible rules/runtime binary.

**Digests:** keep the existing golden snapshot digest unchanged. Storage metadata,
checksums, UUIDs and receipts are excluded from it. Legacy JSON export must preserve
all current array order and JSON escaping/numeric semantics. Full digest comparison
is an O(history + state) audit, not an O(1) per-command operation. Per-row checksums
and an ordered commit-effect hash chain are separate integrity values, not a claim
to have computed the same digest incrementally. An incremental global state root
requires its own specified algorithm and equivalence tests before relying on it.

## 5. Recovery, corruption, import and experimental universes

| Situation | Required behavior |
| --- | --- |
| Exit before SQL COMMIT, including after some RNG/knowledge/job writes | SQLite rolls back the incomplete transaction; load old complete head. Speculative cache/ack is discarded. |
| Exit after COMMIT before acknowledgement | Load the new complete head and return the stored receipt on retry. Do not rerun the command. |
| DB newer than an exported JSON checkpoint/read cache | In managed authority mode the export is stale, not authoritative. Restore DB head; regenerate the export if requested. Keep original files. |
| Export claims a cursor ahead of the DB, wrong universe or wrong head hash | Reject/quarantine that export. Do not fabricate DB history or promote it automatically. |
| Current PR3 mirror/checkpoint disagree during import | Retain the audit's fail-closed behavior. There is no migration authority until an explicit source checkpoint is selected and verified. |
| Missing/damaged read-cache snapshot | Ignore/quarantine accelerator; reconstruct from authoritative SQL revisions. This is not a repair of missing committed history. |
| Missing authoritative event/revision, broken FK/stream count/hash, damaged DB | Stop writes and affected reads; preserve DB/WAL evidence. Restore a separately verified backup into a new path only through an explicit recovery procedure. Never truncate a committed tail to match an older checkpoint. |
| Disk full / BUSY / I/O failure | Roll back when known uncommitted; resolve uncertain COMMIT from receipt. Backpressure/reject admission without skipping scheduled consequences. |
| Incompatible schema/rules/RNG codec | Refuse restore; preserve input. Explicit converter or compatible runtime required. |

Use startup SQLite structural checks/FK checks plus manifest/commit-chain and
stream-boundary checks. Validate row/block digests before use, run full periodic
audits of cold data, and check completeness against counts/ordinals/revisions;
do not use inner joins that hide orphan references. Successful SQLite checks are
not sufficient to prove semantic completeness. A checksum is not authentication
against an attacker who can rewrite every digest. Unread cold data is not declared
fully verified until its audit completes. No automatic salvage or in-place repair.

Signed historical year and simulation-day index are distinct: retain e.g. `-100`
in the event, with current-compatible index day `max(0, year)`. Insertion/commit
time controls when a reference becomes known; an imported ancient event does not
invent ancient knowledge acquisition times. Exact reconstructable state starts
at the imported genesis cut, not at the oldest described historical year.

**Universes:** use one independent database per experiment. A fork records parent
universe, exact committed cut/hash and compatible rules/runtime. For latest-state
forks use SQLite backup, not a copy of a live `.db` without its WAL [S4]. Record
the cut read from the completed consistent copy; verify it before publishing the
child. For a requested historical cut, materialize that cut and only its visible
immutable prefixes into a new database. Never edit/rewind the canonical parent.

Assign a child storage UUID without consuming simulation RNG; preserve domain IDs,
RNG and counters. Receipt namespace includes the request's universe origin so new
child commands cannot collide with copied parent receipts. Identical subsequent
commands must produce identical domain state; divergent rules/seed experiments
need explicit new configuration/version, not an implicit reseed. Initial forks
copy retained data and are O(prefix size), not constant-time copy-on-write forks.
Sharing immutable prefixes is a possible future option-3 migration, not assumed.

## 6. Historical state, snapshots and isolated observation

The authority stores current rows and versioned, complete **storage effects**.
Given genesis/snapshot S and committed cut C, ordered after-images/tombstones for
`S < commit <= C`, plus append-stream visibility at C, reconstruct state without
re-executing gameplay or replaying all human-readable history. A selective query
may instead take the last revision per requested key at/before C. Referenced
knowledge/events are resolved at the same universe and cut, never from current
truth or a later grant. Capture completeness is a future proof obligation (§8).

Multiple commands can share a day. Observation cursors therefore identify
`(universe, committed_cut, schema/codec)`; day queries must specify which cut they
mean. A commit ending at day 10 may contain events at days 3 and 5. **There is no
exact day-5 world snapshot merely because an event description has year 5.**
Initially offer exact committed cuts and explicitly labelled nearest-at/before
results. An exact request inside a committed advance interval is reported as
`not_exactly_reconstructable` until complete intermediate effects or bounded,
version-pinned partial-command replay is independently demonstrated. No invented
interpolation of ecology, knowledge, resources or RNG.

### Snapshot types and publication

1. **Authoritative backup:** a consistent SQLite backup containing all authority
   tables, immutable history/revisions, metadata and referenced codecs. Verify
   restoration in isolation. It is disaster-recovery material and can be large.
2. **Historical state accelerator:** a sealed current-state-at-C image plus exact
   history/revision prefix identities. It can omit event bodies only while those
   remain durably available from the authority. It is not a standalone backup.
3. **Legacy JSON export:** the original complete schema-1 world, still supported
   for small-world interoperability. Its full materialization is not scalable.

Build accelerator snapshots by paging immutable revisions at a fixed logical cut
C into a fresh file/blocks, with lengths, ordering, checksums and version tags.
Rows created after C are excluded. Short queries can use different SQLite read
transactions only because logical revision rows are immutable and never pruned
while referenced. This avoids pinning the live WAL for an hours-long observer.
This logical-cut algorithm needs its own completeness tests; it is not implemented.

Write/fsync/seal/cache-rename/fsync first, then register its digest/cut in SQLite.
Unregistered files are not authority. A missing registered accelerator is a cache
miss, not loss of committed simulation state. Do not move required history out of
SQLite under the same disposable-cache policy. Snapshot retention/compaction may
not remove the only recoverable copy or a prefix needed by any supported cut.

**Readers:** host-authorized, read-only SQLite connections or isolated reconstruction
workers, short transactions, immutable response objects, stable keyset pagination
and explicit row/byte/decompression limits. Never return DB/kernel handles to
clients. Observer queries do not call `advance`, consume RNG, schedule work or
determine which off-screen actors execute. Camera/2D/3D concerns remain outside
authority. Cache eviction changes resource usage, not world existence or knowledge.

Character queries must use only that actor's grants at C. Privileged observer and
raw-history endpoints remain separate. Current PR4 version-1 APIs materialize their
entire requested response; do not silently truncate or change them to meet a new
budget. Add a separately versioned paged contract later, and test disclosure
equivalence over all pages. A character with millions of memories cannot receive
an unbounded list under a bounded response-memory guarantee.

## 7. Scalability, storage budgets and limits

### Population stages — hypotheses, not capacity claims

| Population | Candidate experiment / gate | What remains unproven |
| --- | --- | --- |
| 10,000 | Single local writer; compare full in-memory reference and shadow normalized store, fixed command corpus, cold/warm reads, crash recovery and sustained WAL checkpointing. | Realistic civilization workloads, acceptable per-command latency and write amplification. |
| 100,000 | Indexed due-job pages, batched entity hydration, bounded identity map, lazy knowledge references and byte-limited observer jobs. All consequential jobs still execute in original global order. | Safe replacement of direct dictionary/set access, hot-set size, CPU cost and worst same-day transaction. |
| 1,000,000 | Storage-only feasibility and then equivalent bounded repositories; measure queue/index contention, history growth and backup/reconstruction costs before any realtime claim. | The existing Python object model/heap, single writer and algorithms may fail the budget. Sharding requires a new causality/transaction design, not just more writers. |

A million registered agents is not a million active agents per frame, nor proof
of autonomous planning/ecology. The current project does not implement those
workloads. Do not weaken event fidelity, omit off-screen consequences or introduce
lossy knowledge pruning to achieve a population number.

Illustrative **estimates**: assume 2 KiB serialized current actor data (excluding
knowledge/history/indexes), and one 1 KiB historical event per actor per simulated
day with a 3x allowance for history indexes/witness overhead:

| Actors | Actor payload only | Illustrative history-only growth per simulated day |
| --- | ---: | ---: |
| 10,000 | 19.5 MiB | 29.3 MiB |
| 100,000 | 195.3 MiB | 293 MiB |
| 1,000,000 | 1.91 GiB | 2.86 GiB |

These are arithmetic scenarios, **not measured record sizes, total disk budgets
or promised bounds**. At the million-agent example, 365 simulated days already
exceed 1 TiB history-only before row revisions, snapshots/backups and variable
knowledge. Simulation days per wall second multiply required write throughput.

Budget explicitly:

```text
persistent live disk = current rows + history + witness/knowledge rows + revisions
                     + all indexes + SQLite free pages
transient live disk  = WAL + SHM + temp sorts + snapshot/migration staging
archive disk         = retained verified backups + compressed exports/segments
process memory       = active entity cache + due-job page + query/codec buffers
                     + SQLite page cache + native allocations + Python overhead
host memory          = process totals + OS page cache + other reader/worker processes
```

Repeated RNG states also matter: binary MT state alone is about 2.5 KiB per
changed commit before metadata/compression. Narrative-event rate and command
commit rate are different; do not multiply or hide this cost with an events-only
benchmark. Revisions store changed rows, not a full world per transition.

Candidate **benchmark limits**, not guarantees: actor-cache budgets of 128/256/512
MiB at the three stages, a 64 MiB SQLite cache target per connection, at most two
concurrent reconstruction jobs with 64 MiB each, 8 MiB decoded history-response
pages, and 256-record/4 MiB fetch batches, whichever limit is reached first.
An oversized record needs an explicit bounded streaming path or a clear rejection,
never a silent partial record. Measure metadata/container overhead and native RSS.

SQLite `cache_size` is advisory [S5]; per-connection reader caches multiply. WAL
autocheckpoint thresholds are not a hard WAL size cap: long readers can prevent
checkpoint completion [S1]. Start experiments with a 64 MiB checkpoint target,
observe tail latency and pinned readers, and apply admission backpressure around
a separately configured emergency disk/WAL watermark (illustratively 512 MiB).
Never delete WAL files to enforce a quota. Limit read transaction duration and use
bounded retries/cancellation of *observation*, not loss of simulation events.

Track write/read page amplification, `BUSY`, COMMIT latency, checkpoint progress,
RSS/native/cache memory, temp spill, main/WAL/SHM separately, backlog, bytes per
knowledge grant, reconstruction latency and total backup footprint. On bounded
CPU/I/O, simulation can run slower; determinism does not imply realtime performance.

### Compression and large history

Keep indexed IDs, commit/day keys and references directly queryable. Cold bodies
can later be sealed into independently decompressible blocks **inside the same
authority database**, with per-record location/length/index and per-block codec,
uncompressed size and checksum. Prototype zlib first because it is available in
the standard library. Dictionary/Zstandard/LZ4 choices require separate license,
seek amplification and CPU benchmarks; none is adopted here.

Do not decompress a monolithic lifetime archive for a small query. Enforce byte
and expansion limits before decoding blocks. Preserve canonical record bytes and
all references across compression. An explicit verified copy migration can change
physical encoding; do not silently delete original authoritative rows/files.
Moving mandatory blocks to external segments is deferred option 3, with a required
manifest/fsync/fork/GC protocol and a separate approval gate.

## 8. Phased migration and executable acceptance gates

The commands below are the required test contracts for future implementation PRs,
not claims that unimplemented adapters/tests exist. Phase 0 commands run now.
Each later phase must supply the named test modules and pass its command **before**
the next phase starts; absence is a failed gate, not a skipped success. Run all
gates on Python 3.12 and 3.13, supported SQLite versions and the targeted filesystem.

| Phase | Change / reversibility | Executable gate and required assertions |
| --- | --- | --- |
| 0 — this design only | Pinned source inspection, external references and temporary probe. No import/mutation integration. | `python docs/architecture/experiments/sqlite_authority_probe.py`; `(cd prototype && python -m unittest discover -s tests -v)`. Eight probe tests + 74 foundation tests on each runtime. |
| 1 — smallest next task | New opt-in `snapshot_authority` store in a separate implementation PR; complete existing JSON snapshot in one DB transaction, receipts and version gates. Existing kernel/ledger/save paths unchanged. Copy-only genesis import. | `(cd prototype && python -m unittest discover -s tests -p 'test_authority_snapshot.py' -v)`. Exact encode/decode/digest equality, byte-unchanged source saves, RNG/queue/knowledge, negative years, >64-bit IDs/day/sequence, insertion order, unknown versions, crash before/after COMMIT, duplicate-key receipt and FK/corruption rejection. |
| 2 — normalized shadow | Define canonical rowization covering every field in `encode`; full before/after snapshot diff is allowed as a slow **test oracle**, not production performance. Store current rows + revisions + histories atomically in a new target; source remains authority. | `python -m unittest discover -s tests -p 'test_authority_shadow.py' -v` from prototype. Deterministic generated command corpus plus every public mutator; export equality after every command; no missing fields, no history rewrite, complete typed references, exact ordering and same-day ties. New/unknown codec fields must fail rather than disappear. |
| 3 — explicitly approved small-world cutover | Only after phase 2, introduce gateway/transaction barriers and SQL durable authority; RAM remains a full disposable cache initially. No mirror/JSON dual-primary writes. Preserve original saves and a rollback deployment path. | `python -m unittest discover -s tests -p 'test_authority_recovery.py' -v`. Execute full §9 matrix, including ambiguous COMMIT/ACK, stale cache, rejected travel, day-only advances, no-op teaching, in-flight arrival+research, gauss cache, independent universes and old-save restoration. No double RNG draw or changed golden digest. |
| 4 — bounded repositories and observers | Only then replace whole-history dictionaries/knowledge sets with tested repository protocols and byte-budgeted caches. Preserve the old full-view API separately; add a versioned paged API. | `python -m unittest discover -s tests -p 'test_authority_lazy_views.py' -v`. Paged union equals reference, no cross-character/universe/cursor leakage, unchanged old snapshots, no observation mutation, bounded payload/native memory and due-job order. Storage stress at 10k/100k/1m with CPU/RSS/WAL reports; population targets remain gates, not assumed successes. |
| 5 — historical cuts / snapshots | Expose the already captured complete revisions through full as-of reconstruction; generate verified logical-cut accelerators without a live long reader. Source authority retained. | `python -m unittest discover -s tests -p 'test_authority_historical_cuts.py' -v`. Compare every supported cut against captured reference states; tombstones, retro history, late claims, boundaries inside advance explicitly unsupported until proven, missing snapshot falls back without dropping data. No full-lifetime replay per request. |
| 6 — physical compression / optional future segments | Explicit new-format copy, exhaustive content/reference verification and retained old database. External authority segments require a new ADR; not automatic phase-6 approval. | `python -m unittest discover -s tests -p 'test_authority_storage_conversion.py' -v`. Lossless byte/ID/grant equivalence, random seeks, block corruption, size-limit/decompression failures, interrupted conversion, backup restore and source immutability. Measure total disk including WAL/temp/backups. |

For phases 1–6 also run the full existing suite and unchanged rules-v2 golden
test. Test command generation uses a separate harness RNG, never the world's RNG.
Record deterministic workload/rules/runtime/codec versions and physical storage
settings with every benchmark. Do not interpret a passing small fixture as a scale
gate or hide missing archive/view prerequisites behind an aggregate pass count.

Import uses the explicit selected complete unified checkpoint as authority, after
strict validation. A matching modern archive can be cross-checked read-only; a
legacy archive alone lacks RNG/current state and cannot become a universe by
guesswork. Never call an archive writer constructor that might create missing
schema in the source during conversion. Legacy `sim.py` saves are a different
format: retain their compatible runtime or reject unsupported conversion clearly.
All conversions write a new path, verify the original full digest/ordinals/grants,
retain input files and record source hashes. Switching authority is explicit and
reversible by keeping the old deployment and compatible exports; it does **not**
permit rewinding a world that has already accepted later committed commands.

## 9. Fault-injection matrix

P = exercised in the isolated probe on small complete snapshots; A = established
by the pinned integration audit; D = required future adapter test, **not proved**.

| Fault or boundary | Expected result / invariant | Evidence / next gate |
| --- | --- | --- |
| After writing candidate state/head, before related history/knowledge | Entire transaction absent after reopen; exact old RNG/queue/knowledge | P process exit; D phase 1 normalized case |
| After history/witness/knowledge writes, before COMMIT | No partial rows/indexes/receipt; old state | P process exit; A archive insertion faults; D all normalized families |
| Witness FK failure / duplicate event ID / invalid actor | Rollback complete transition; no orphan/index drift | P FK; A duplicates/typed witness faults; D production constraints |
| After COMMIT, before ACK | Exact new state; same-key retry returns receipt, no second command/RNG use | P; D phase 1 genuine host-command execution |
| Same request key with different command; stale parent | Reject without state change | P fixture identity comparison; D canonical request hashing |
| BUSY/FULL/IOERR, including uncertain COMMIT return | Resolve receipt; do not resume speculative cache | D phase 3 filesystem/I/O harness |
| Reader while writer commits | Consistent old read cut, then new cut after transaction; read-only writes rejected | P; D production paged knowledge joins |
| Long reader prevents WAL reuse / interrupted checkpoint | Preserve committed head; backpressure/cancel reader; no manual WAL deletion | SQLite [S1]; D measured phase 3/4 |
| Export/cache older or newer/wrong universe | Stale cache ignored or foreign/ahead export rejected, no authority rollback | A old mirror mismatch detection; D new authority precedence |
| Tampered snapshot body / missing persisted witness row | Detected, retain damaged evidence; no automatic repair | P; A broader archive corruption; D all authority row/revision families |
| Missing/tampered revision or reordered provenance | Fail on checksum/count/order audit; no reconstructed fiction | D phase 2/5 |
| Unsupported rules/storage/revision/RNG codec | Refuse before mutation; retain input | A checkpoint rule gate; D phase 1 storage gates |
| Snapshot staged/sealed but not cataloged; cataloged cache lost | Ignore orphan accelerator / regenerate from SQL; never lose authority | D phase 5 |
| Backup/fork, child commits after parent copy | Parent byte/domain state unchanged; child initially same RNG/state, independently writable | P consistent-copy fork; D historical-cut fork and lineage/receipt namespaces |
| Interrupted schema/compression migration | Original fully usable; incomplete target never selected | D phases 1/6 |
| Physical power cut / torn storage / filesystem failure | Durable old-or-new head under documented platform guarantees, otherwise fail closed and restore verified backup | Not tested; dedicated deployment validation required |

Do not automatically truncate an archive, delete orphan historical rows, mark a
failed migration successful, recompute corrupted digests, or lower rules versions
to make tests pass. Ordinary SQLite removal of **uncommitted** work on recovery is
not truncation of committed simulation history.

## 10. Evidence, risks and unresolved questions

### Proven by inspection or scoped tests

- Current kernel mutates state beyond narrative history; current codec captures
  RNG, queue, knowledge, provenance, order and all fields listed above.
- PRs remain unmerged siblings on the verified foundation.
- On Python 3.12.14 / SQLite 3.53.1 and Python 3.13.5 / SQLite 3.46.1, the
  accompanying probe passed eight cases: rollback, three process-exit subcases,
  idempotency/parent checks, read isolation, independent backup fork, corruption,
  missing memories and committed-cut continuation including signed history.
- The untouched foundation suite passed 74 tests on both runtimes, including the
  existing golden digest `dd4d13c358216e612383655f5aee38e3acc40d94172e9a08e0990ce5baba5193`.

The probe stores a complete growing JSON snapshot on **every** test commit and
performs full scans. It does not prove normalized captures, cross-version command
replay, intermediate-day reconstruction, bounded RAM, power-loss guarantees or
large-agent throughput. It is intentionally unsuitable as production persistence.

### Measured, limited compression experiment

Five synthetic travel/research rounds (50 days), existing benchmark fixture,
zlib level 6, exact decompression and legacy digest roundtrip on both runtimes:

| Agents | History events | Full JSON bytes | Compressed bytes |
| --- | ---: | ---: | ---: |
| 100 | 2,000 | 197,805 | 26,354 |
| 1,000 | 20,000 | 1,993,873 | 217,819 |

This is roughly 7.5x/9.2x compression on repetitive synthetic **full snapshots**,
not a ratio for normalized rows, arbitrary worlds, random-seek blocks or total
disk including indexes/WAL. Timings are single local observations, not targets.
Raw results, pinned heads and fetched-source provenance are in
[`authoritative-persistence-evidence.json`](authoritative-persistence-evidence.json).

### Risks / decisions still open

1. **Capture completeness:** all direct mutators/order-sensitive fields must be
   fenced and covered. This is the largest migration risk; no live cutover yet.
2. **Atomic advance size:** worst same-day work may exceed acceptable lock, WAL,
   latency or working-set budgets. No unapproved splitting/semantic changes.
3. **Revision and knowledge growth:** lossless retention is not constant disk;
   million-agent feasibility and compressed indexed blocks require measurements.
4. **Historical time contract:** arbitrary times inside public commands are not
   exact committed states. Future finer-grained capture/replay needs proof.
5. **Integrity cost:** row hashes do not prove a complete state root; full cold-data
   audits, counts and revision equivalence can be expensive. Incremental roots are
   unspecified until benchmarked and independently verified.
6. **Platform/runtime:** WAL needs supported local locking; FULL assumes honest
   fsync. Python RNG compatibility and SQLite feature versions must be pinned;
   Rust equivalence and cross-host replication are not demonstrated.
7. **Schema/number conventions:** finalize concrete STRICT-table DDL, indexes,
   decimal-key bounds and binary RNG codec through phase-1/2 tests, not implicit
   integer casts or silent input rejection of otherwise valid existing saves.
8. **Operating policy:** define recoverable backup schedule, disk reserve,
   corruption escalation, observation deadlines and explicit retention authority.
   Cache GC is different from permission to discard committed history.
9. **Release policy:** source LICENSE remains unfinished under the existing IP
   policy; no third-party source code or assets were copied into this proposal.

## 11. Smallest safe next implementation task

Implement **only a copy-only, opt-in SQLite snapshot-envelope store** on a separate
branch after this proposal is reviewed. API sketch:

```text
create_from_unified_snapshot(snapshot, new_path, source_hash) -> import_receipt
commit_snapshot(snapshot, expected_parent, request_key, request_hash) -> receipt
load_snapshot(committed_cut=None) -> original schema-1 snapshot
```

It must use one transaction for complete state + commit metadata + receipt, enforce
format/rule checks, preserve the exact legacy digest and ordering, and pass phase-1
crash/idempotency/corruption/import tests on both runtimes. Preserve original saves
byte-for-byte; never open/migrate PR3 databases in place. No hooking `advance`, no
replacement of `HistoricalLedger`, no normalized production row capture, no lazy
kernel rewrite, no changed viewer output and no authority cutover in that task.

Check the actual SQLite value/parameter limits before accepting an import. The
phase-1 full JSON BLOB has a finite size limit; an oversized existing save must be
rejected clearly with its source untouched, not truncated or declared migrated.
Normalized/chunked support belongs to a later explicit converter. Do not raise
process limits or claim every conceivable old world fits the stepping-stone store.

Acceptance requires a new implementation test module with the phase-1 command,
all existing tests and independent reopen/continuation assertions. A complete
snapshot-per-commit store is a correctness stepping stone, explicitly O(full
state/history) in memory/I/O. Its success authorizes evaluating phase 2, not claiming
that the whole proposed architecture is implemented or scalable.

## 12. Research and primary references

Existing research reviewed: [reuse audit](../research/reuse-audit.md),
[simulation foundations](../research/2026-11-04-multilingual-simulation-foundations.md),
renderer-independent ADR and pinned temporal-observation/audit documents above.
Candidate engine/population claims in those notes remain unverified. The temporal
document references `lossless-storage-research.md`, but that file is absent in the
inspected trees; this proposal does not pretend to have reviewed it.

Primary sources fetched 2026-11-05, used for techniques rather than copied code:

- **[S1]** [SQLite WAL](https://www.sqlite.org/wal.html): one writer, concurrent
  readers, checkpoint starvation, local-host restriction, attached-DB atomicity.
- **[S2]** [SQLite isolation](https://www.sqlite.org/isolation.html): read snapshots,
  `SQLITE_BUSY_SNAPSHOT`, `BEGIN IMMEDIATE`.
- **[S3]** [SQLite transaction control](https://www.sqlite.org/lang_transaction.html)
  and [atomic commit](https://www.sqlite.org/atomiccommit.html): commit/rollback,
  error handling and underlying storage assumptions.
- **[S4]** [SQLite backup API](https://www.sqlite.org/backup.html): consistent copies
  and incremental backup; do not copy only the live database file.
- **[S5]** [SQLite PRAGMAs](https://www.sqlite.org/pragma.html): foreign keys outside
  transactions, FULL synchronization, cache targets and integrity checks.
- **[S6]** [SQLite limits](https://www.sqlite.org/limits.html): bounded SQL values,
  file/page limits and reasons to test actual builds.
- **[S7]** [Microsoft event sourcing pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing):
  event versions, snapshots, projection complexity and context for rejecting a
  premature descriptive-event journal as authority.

Source URL/title/response hashes and executed results accompany this ADR. General
storage techniques are established; their performance and correctness as a Living
Universe production adapter remain acceptance obligations, not inherited guarantees.
