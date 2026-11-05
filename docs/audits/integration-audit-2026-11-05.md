# Living Universe integration audit — 2026-11-05

## 1. Executive result

Both PRs were inspected at pinned commits, tested independently on Python 3.12
and 3.13, and tested together in a local temporary branch. Neither PR was merged
or retargeted. No simulation redesign, rendering, physics, paid dependency or
private research material was introduced.

The foundation and viewer implementation passed their original suites. PR3's
original suite had three failures and two skips caused by empty history fixtures.
Additional fault-injection tests reproduced real archive/publication defects:
inconsistent witness rows could commit; full mirror verification omitted auxiliary
tables; recovery could replace an older checkpoint before validating the archive;
identical prepared publications could leave a blocking candidate; and the optional
writer differed from kernel ID allocation and consumed iterator witnesses.
Append/publication also committed a caller's already-open transaction implicitly.

Focused fixes are on the existing branches. All final local suites pass on both
runtimes: foundation 74, PR3 141, standalone PR4 83 executed plus four explicit
integration skips, and the combined checkout 154 with no skips. The existing
rules-v2 golden digest remains unchanged. Source-fix CI logs independently confirm
the same PR3/PR4 counts on Python 3.12 and 3.13.

The SQLite code is suitable for review as an **opt-in mirror/experimental archive**.
It is not yet an authoritative, bounded-memory replacement for live kernel history.

## 2. Actual branch dependencies

Default branch: `main`. Foundation: `codex/stabilize-foundation`, PR1, still unmerged.

| Branch/PR | Base commit | Originally inspected head | Source-fix head |
| --- | --- | --- | --- |
| `main` | — | `2872624c1a5b109b311704d7db4d1a1ffae7f98c` | unchanged |
| Foundation / PR1 | `main` | `a1b455006d489dd7275aff47fcbe2b498aae139d` | unchanged |
| PR3 `feature/sqlite-history-ledger` | `a1b455006d489dd7275aff47fcbe2b498aae139d` | `7bb3d8048dd3b599cd2c3831f694b4f1fc07e13e` | `a8fd5f0a14517ffb458e869152025e7ddf6821c2` |
| PR4 `codex/viewer-independent-projections` | `a1b455006d489dd7275aff47fcbe2b498aae139d` | `ef72e34545175fdc78dafa3ed49e1f52341bdb72` | `523e7e1bcbf8854132ae60b44307475069291cb4` |

```text
main 2872624
└── foundation a1b4550 (PR1, four commits ahead of main)
    ├── PR3: 7bb3d80 → a8fd5f0 (archive fixes; report-only commit follows)
    └── PR4: ef72e34 → 523e7e1 (viewer tests and boundary documentation)
```

PR3 and PR4 are siblings, not stacked on each other. PR4 depends on the unmerged
foundation, not PR3. Its new optional integration tests skip explicitly when the
archive modules are absent.

The actual comparison showed a common merge base of `a1b4550`, 65 PR3 commits
and one PR4 commit. PR3's 65 commits form a linear chain: no merge commits, empty
tree repetitions or non-linear parents. Several subjects repeat, but the trees
differ; repeated subjects are not duplicated final changes. The original PR3 diff
adds 27 archive-related files, tests and temporal-observation documentation; it
does not modify kernel mechanics. PR4's seven-file diff contains the view module,
its tests and related documentation. No unrelated source modifications were found.
The creator NOTICE and release policy belong to the common foundation and were
preserved. Additive integration encountered no overlapping patch conflicts.

Recommended order, subject to explicit merge approval: **PR1 → PR4 → PR3**. Once
PR1 is merged, retarget the siblings to main, then rerun CI on the combined PR3
base after PR4 lands. Either sibling can technically follow the foundation first;
the suggested order reviews the smaller viewer increment before the larger archive.

## 3. Environment and executed commands

Linux x86_64, kernel `6.18.57`, glibc 2.41. Local interpreters:

| Command | Python | SQLite library |
| --- | --- | --- |
| `python3` | 3.12.14 | 3.53.1 |
| `python3.13` | 3.13.5 | 3.46.1 |

Only the documented Python standard library is needed; no pip packages or external
services were installed. The existing Python 3.12 virtual environment was available;
the independently installed 3.13 interpreter was also exercised. Files were fetched
through the GitHub connector because the earlier workspace Git proxy was unavailable.
Exported local tree hashes matched the actual remote trees before edits:

- Foundation: `82f3d2e4b54edf0aed3a304ecfd6680d2ea9aad0`.
- Original PR3: `47cd29e552fb46dccbdfe65a33e790e71b2fe0f7`.
- Original PR4: `5e3759746ffc7e31b9ca03a75dc63c826730eb88`.

For every checkout below, the exact full-suite commands were:

```sh
cd /workspace/<checkout>/prototype
python3 -m unittest discover -s tests -v
python3.13 -m unittest discover -s tests -v
```

Checkouts: `audit-foundation`, `audit-pr3`, `audit-pr4`, `audit-combined`.
The PR checkouts were first tested at their original heads and again after changes.
As documented in the repository, sibling-module imports require this working
directory. One repository-root discovery attempt was corrected to this command;
its import errors were not counted as simulation regressions.

| Checkout/state | Discovered, on each runtime | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Foundation `a1b4550` | 74 | 74 | 0 | 0 |
| Original PR3 `7bb3d80` | 119 | 114 | 3 | 2 |
| Original PR4 `ef72e34` | 81 | 81 | 0 | 0 |
| Fixed PR3 `a8fd5f0` | 141 | 141 | 0 | 0 |
| Updated PR4 `523e7e1` | 87 | 83 | 0 | 4 |
| Temporary union of both updated heads | 154 | 154 | 0 | 0 |

The three original failures were `test_mismatch_restores_original_mapping`,
`test_archive_behind_checkpoint_rejected` and
`test_recovery_does_not_publish_unverified_archive`. Their fixture had no events;
the alleged mismatch or SQL corruption therefore did not exist. Two epistemic
tests skipped for the same reason. Fixtures now schedule actual research history,
assert required actors/events and exercise the original corruption expectations.
The witness-insertion regression now uses a SQLite trigger after an earlier
witness insert, rather than relying on a duplicate that is rejected in preflight.
The separate duplicate-row regression is retained.

The first independent regression run against original PR3 discovered 12 methods
and produced 15 failing subcases and four errors. Additional original-head
reproductions confirmed the identical-candidate defect and transaction ownership
problem (four failing subcases across two methods). Final regressions all pass.

Reproduction command from `prototype/`:

```sh
python3 -m unittest discover -s tests -p test_archive_audit.py -v
python3 benchmark_archive_audit.py
```

The CI workflow uses `ubuntu-latest`, read-only repository permissions, Python
3.12/3.13 and `python -m unittest discover -s tests -v` from `prototype/`.
Original PR3's actual head had failed CI; original PR4's had passed.
Inspected source-fix CI runs and logs:

- PR3 [run 41990894208](https://github.com/nivednb/living-universe/actions/runs/41990894208):
  141 tests, no skips, both matrix jobs successful, head `a8fd5f0`.
- PR4 [run 41990895417](https://github.com/nivednb/living-universe/actions/runs/41990895417):
  87 discovered / four skips, both matrix jobs successful, head `523e7e1`.

This report is added in a subsequent documentation-only PR3 commit; its actual
latest-head CI is checked separately in the audit handoff. Structured evidence:
[`verification-2026-11-05.json`](verification-2026-11-05.json).

## 4. Confirmed defects and fixes

Severity refers to the affected opt-in archive path; it does not imply the live
kernel was already using SQLite as its sole store.

| ID / severity | Defect and reproduction | Fix / affected files |
| --- | --- | --- |
| D1 High | Prepare a newer candidate, leave an older public checkpoint, corrupt the archive, then recover. Recovery raised only after replacing the old checkpoint. | Validate candidate/checkpoint, index, payloads and witness rows before rename; preserve files and prepared intent on failed validation. `checkpoint_publication.py`, `history_archive.py`. |
| D2 High | Supply witness rows for another event, omit a declared witness, or pass boolean/fractional/string actors to low-level append. Some inconsistent rows committed. | Exact typed row-to-payload equality before writes; reject duplicates, invalid IDs, orphan/omitted rows and witnesses without same-batch events. Persist event + ID + witnesses through the existing single transaction. `sqlite_history.py`. |
| D3 High | Delete ID mappings or witness rows while canonical event payloads still match the world. `verify_history` accepted the mirror. Boolean/float witness payloads could compare equal to integers. | Full auxiliary-table audit and strict historical field types, including reads of re-encoded payloads. `history_archive.py`, `atomic_witness_archive.py`, `sqlite_history.py`, `archived_events.py`. |
| D4 High | Pass a one-shot witness iterator to the writer. Validation consumed it, then the event recorded no witnesses. | Materialize the iterator once before validation and construction; persist its witness rows atomically. `archive_writer.py`. |
| D5 Medium | Seed `kernel-1`, reserve `kernel-2`, then generate an event. The writer collided rather than matching the kernel's `kernel-3`. | Match the kernel's collision-skipping allocator. Explicit user-supplied reserved IDs still fail. `archive_writer.py`, kernel-parity regression. |
| D6 Medium | Recover an identical prepared candidate while the old destination already has the same bytes. Recovery left the recognized candidate behind and blocked the next publication. | Prefer and consume the digest-matching, validated candidate; do not remove unrelated candidates. `checkpoint_publication.py`. |
| D7 Medium | Crash after rename but before directory fsync, then recover from the matching destination. Recovery marked published without repeating directory fsync. | Fsync the directory on every prepared recovery before final status. `checkpoint_publication.py`. |
| D8 Medium | Start an unrelated SQL transaction, then call append/publication. The connection context could commit unrelated caller changes. | Append, publication and recovery reject pre-existing transactions instead of taking ownership of them. `sqlite_history.py`, `checkpoint_publication.py`. |
| D9 Medium | Append a witness-enabled event into a nonempty legacy archive without witness schema. The code silently created a schema missing old memories. | Reject implicit upgrade. Fresh exports include witness rows; legacy event readers remain available, but incomplete mirrors cannot publish/recover. `sqlite_history.py`, `history_archive.py`. |
| D10 Medium | Three failing tests and two skips gave no meaningful archive corruption evidence. | Populate fixtures; retain/strengthen corruption and rollback assertions. Six existing test files plus `test_archive_audit.py`. |

Fix commits:

- PR3 [`a8fd5f0a14517ffb458e869152025e7ddf6821c2`](https://github.com/nivednb/living-universe/commit/a8fd5f0a14517ffb458e869152025e7ddf6821c2):
  six archive implementation files; six existing archive test files; new
  `test_archive_audit.py` (22 methods with additional subcases) and allocation probe.
- PR4 [`523e7e1bcbf8854132ae60b44307475069291cb4`](https://github.com/nivednb/living-universe/commit/523e7e1bcbf8854132ae60b44307475069291cb4):
  `test_view_audit.py`, `test_view_archive_integration.py`, `view-contract.md`.
  No viewer implementation defect required changing `views.py`.

No changes to `unified_kernel.py`, the golden assertion, simulation rules version
2, checkpoint schema 1 or view schema 1. Golden digest, tested on both runtimes:
`dd4d13c358216e612383655f5aee38e3acc40d94172e9a08e0990ce5baba5193`.

## 5. Persistence guarantees actually established

### SQLite event transaction

The event, event-ID index and exact witness rows are inserted inside the same
ledger-owned SQLite transaction. Trigger failures at event insertion, ID insertion
and the second witness insertion roll back all three tables. Duplicate event IDs,
duplicate witness rows and invalid witness IDs leave no new records. A real child
process exit during the second witness insertion also rolled back on reopen.
DDL can leave an empty witness table after a failed first write; this is not a
partially committed historical event.

Audits detect missing/extra/orphan witness rows, incorrect actor mappings, damaged
ID indexes, malformed/re-encoded payloads and absent witness schema, including
after reopening. The LEFT JOIN retains orphan rows; the end-of-stream check does
not hide them. SQLite foreign-key enforcement is not enabled: safety relies on
the validated API plus audits, not on trusting arbitrary writes to the raw `db`
handle. That handle is not an untrusted-client capability.

Historical adapters require contiguous sequences for kernel history; the generic
ledger's documented contract permits increasing sequences with gaps. Noncontiguous
kernel history is rejected by the writer/mirror gates. Simulation index days are
nonnegative and monotonic. Signed historical years are preserved in payloads;
negative years index at day zero and survive reopen. Live writer calls continue
to reject negative simulation days. Event-ID allocation now matches the kernel.

Legacy archives without persisted witnesses are **not silently upgraded**. An
explicit ID-index rebuild exists and is transactional; it is not a witness-memory
migration. Nonempty pre-witness archives can be read, but modern mirror verification,
publication and recovery refuse them. Designing a lossless witness migration is
outside this audit. Preserve old stores and checkpoints for explicit operator review.

### Checkpoint protocol: recovery versus detection

| Interrupted state | Verified behavior |
| --- | --- |
| Partial checkpoint write / exit before publication intent commit | No new public checkpoint; unrecognized pending file is retained and blocks overwrite. A valid previously published record can still recover its older checkpoint if its history matches. No guessing about the orphan candidate. |
| Exit after SQLite intent commit, before rename | A digest-matching candidate is fully loaded and archive-verified, then renamed, directory-fsynced and marked published. |
| Exit after rename / before status commit | Matching public bytes are fully verified; directory fsync repeats before status finalization. |
| Exit after final publication status commit | Published checkpoint and archive reopen successfully. |
| Candidate missing/corrupted and no destination matching the intended digest | Fail closed; retain any older checkpoint, archive and prepared metadata. No fabricated recovery. |
| Candidate hash matches but checkpoint semantics/archive are invalid | Reject before replacing the old public checkpoint. |
| Identical old destination and recognized prepared candidate | Consume the verified candidate and allow future publication. |
| SQLite event archive ahead of checkpoint | Reject; do not truncate the tail or silently accept the stale checkpoint. **Detection only**, not automatic world reconstruction. |
| Checkpoint ahead of archive | Reject; do not fabricate missing events. **Detection only**. |

Actual process exits exercised before intent, after intent, after rename, before
published-status update and after status completion. Separate injected write/fsync/
replace tests cover JSON checkpoint interruption. Ahead/behind mismatch tests
explicitly assert that existing checkpoint bytes and archive cursors are unchanged.

Publication coordinates a checkpoint with an **already committed exact mirror**.
It does not atomically commit live simulation commands, claims, beliefs, all memories
and an external JSON file as one operation. There is no causal replay log capable
of repairing arbitrary archive/checkpoint divergence. Retain the in-memory kernel
and full checkpoint as current authority until a separate design is approved.

WAL + synchronous FULL and POSIX directory fsync are configured/exercised, but
physical power interruption, device failure and Windows/macOS durability were not
tested. Concurrent writers and concurrent kernel mutation are unsupported.

## 6. Memory and scalability audit

Let N = archived events, W = witness rows, B = caller batch, K = requested/cached
events, A = actors. Costs also depend on maximum payload/witness size.

| Operation | Data/complexity characteristics |
| --- | --- |
| `append_many` | Materializes the entire supplied batch and witness rows; O(B + batch witness count) Python storage, not an unbounded-input streaming append. Inserts use SQLite B-tree indexes. |
| `iter_events` | Fetches batches (default 256) and verifies each payload; O(N) scan, O(batch payload bytes) Python working storage. Filtered queries can incur SQLite sorting/planning costs. |
| ID-index audit / rebuild | Full scan; rebuild inserts bounded batches in one transaction. Python working storage is batch-sized; SQLite indexes/journals/temp storage are additional costs. |
| `get_event_by_id` / `ArchivedEvents` | First lookup per session performs O(N) validation; warm indexed lookup is O(log N) plus payload decoding. No persistent Python event-object cache. |
| `verify_witness_memory` | Full event/index scan and ordered witness join; Python memory is batch/largest-event sized. ORDER BY may require SQLite-managed temporary sorting over W rows; not a strict total-memory guarantee. |
| `export_history` | Batches 256 events, but reads an already fully resident kernel. Commits per batch; later failure can retain an internally consistent exported prefix. It is not an all-history transaction. Re-export to nonempty stores is refused, not automatically cleaned up. |
| `verify_history` | Streaming archive scans, but the comparison world already owns all events/memories. O(N + W), potentially plus database sort costs. |
| Archive epistemic audit | Streams events and performs indexed reference lookups; existing actor/claim/knowledge sets remain resident. No replacement of the live knowledge model. |
| `probe_archived_kernel` | Temporarily swaps a read-only mapping and restores it; live invariant checks still build sets of historical references, and snapshots fully materialize history. Not bounded-memory saving. |
| `snapshot_with_archive`, JSON encoding/loading/publication | Full historical event lists and/or full restored worlds are materialized, proportional to N and knowledge size. |
| Historical event window | Bounds event count, not bytes; arbitrary payload size and SQLite query sorting remain unbounded by that setting. Cache currently retains records but is not used to answer repeated queries. |
| Character view | Builds a detached view proportional to the actor's acquired memories/claims; these reference sets remain in RAM. Arrival lookup scans pending events. |
| Observer view | Copies requested actors plus all settlements/resources/residents/routes; actor filtering does not remove the full settlement graph. |

Measured additional Python peak allocation (tracemalloc, fixed small payloads):

| Operation | 1,000 events | 10,000 events |
| --- | ---: | ---: |
| Streaming iteration | 211,563 bytes | 212,109 bytes |
| ID-index audit | 211,343 bytes | 211,890 bytes |
| Witness audit | 211,706 bytes | 212,252 bytes |
| One full append batch | 464,140 bytes | 4,702,732 bytes |
| Full live snapshot, excluding already allocated world | 669,436 bytes | 6,055,396 bytes |

These measurements support bounded **Python batching for fixed-size records**,
not bounded total RSS or authoritative history. tracemalloc excludes SQLite/native
allocations and the world's pre-existing history. The probe's witness rows are
empty; correctness tests separately cover nonempty witness persistence.

The main database file alone was 4,096 bytes in both samples while open WAL files
held 333,752 and 2,579,152 bytes respectively. The older lookup benchmark's
`db_bytes` is main-file size, not total storage footprint. The new probe records
main/WAL/SHM separately. Raw results and reproduction code:
[`archive-allocation-2026-11-05.json`](archive-allocation-2026-11-05.json),
`prototype/benchmark_archive_audit.py`.

## 7. Verified viewer and integration boundaries

No kernel, RNG, queue, ledger or mutable world containers are reachable through
the declared view fields. Frozen records contain copied primitives and tuples;
wire dictionaries/lists are fresh copies. Tests change nested wire data, bypass
frozen assignment via `object.__setattr__` / `__dict__`, advance authoritative state
after capture and verify unchanged old snapshots and authoritative digests.

Frozen Python dataclasses are conventional immutability, **not an arbitrary-code
sandbox**. A malicious Python caller can edit its detached view object; these
edits do not affect the kernel. Trusted host code must authorize observer access
and bind character identity. The library is not a network authentication server.

Character projections reveal self state and acquired techniques/memories/claims/
beliefs, not other actors' hidden knowledge, RNG, destiny, checkpoint internals,
unwitnessed event truth, private evidence or global observer data. Historical
statements already witnessed or communicated are intentionally visible. Observer
projections are explicitly privileged; actor selection is presentation filtering,
not a confidentiality boundary. Historical event windows are privileged archive
inspection, not a character-filtered observation endpoint.
Their SQL actor filter matches the record's actor column, not its witnesses;
exported historical records use a null actor. It must not be mistaken for
witness-memory filtering or character authorization.

The local temporary branch `audit/combined-no-merge` applied the two branches'
additive file changes without merging either PR. Tested union tree:
`7653227fe73661f143bd8dff410029ba53574163`.
Four optional integration tests ran there without skips and proved:

1. Character and observer messages match in-memory versus archived-event mappings;
   archive logical rows and authoritative state remain unchanged by requests.
2. Verified checkpoint publication/recovery followed by view construction matches
   the original view and deterministic continuation.
3. Archived claim references do not reveal unwitnessed historical truth.
4. Independent historical windows do not change current day, RNG or pending work.

The archive mapping was substituted only inside a host-controlled test scope,
then the original mutable event dictionary was restored before advancement.
No production integration from kernel to renderer or archive was introduced.

## 8. Remaining risks, in priority order

1. **High / blocks primary-store migration:** there is no single durable commit
   spanning live state, all epistemic state and checkpoint publication. Archive
   ahead/behind is detected, not reconstructed. Do not remove authoritative RAM
   history or treat the archive as an automatic recovery source.
2. **Medium:** total history, witness knowledge, full checkpoints and character
   views still grow with retained information. Byte-budgeted cache/queries and
   streaming snapshots are not implemented. No bounded-memory claim is justified.
3. **Medium:** export is atomic per batch, not per complete export. Interrupted
   pre-intent candidates and legacy witness migrations require explicit operator
   handling. Files/data are deliberately retained rather than silently repaired.
4. **Medium:** trusted single-writer/synchronized-host assumption; SQL handles and
   Python objects are not hostile-client security boundaries. Hashes are integrity
   checks, not authentication against an attacker who can rewrite all metadata.
5. **Medium:** power-loss/device/other-OS guarantees remain untested. No silent
   schema migration policy has been added for future formats.
6. **Low / release governance:** the existing policy intends Apache-2.0 for code,
   but a canonical source LICENSE is still absent. NOTICE, documentation licensing
   and differentiated research/data release policy are preserved.

## 9. Merge recommendation

- **PR4:** ready for review after the foundation; viewer semantics were unchanged.
  Four skipped tests on its standalone CI are intentional and all pass in the
  combined checkout. Retarget/recheck against main after foundation approval.
- **PR3:** repaired and green for review as an opt-in archive/mirror experiment,
  with legacy/migration restrictions stated above. **Blocked as a replacement for
  authoritative live persistence or a bounded-memory engine.** Consider squashing
  its long incremental history when approving integration; no history was rewritten
  during this audit.
- **No merges performed.** Final latest-head status and commit links are provided
  with the audit handoff; source-fix CI evidence is recorded above.

## 10. One recommended engineering milestone

**Approve a single-authority persistence design before migrating live history.**
This is a proposal/design milestone, not authorization to implement a redesign.
Acceptance criteria:

- Specify the authority and durable commit boundary for events, witness memories,
  communicated claims/beliefs, world state and checkpoint cursors.
- Define recovery for every archive-ahead/behind and publication state, preserving
  all committed history; no automatic truncation or unapproved legacy migration.
- Define signed-year/ID compatibility and keep the existing deterministic rules
  unless an independently explained rules change is approved.
- Identify which APIs can stream and which require full history; set explicit
  byte budgets and a measurement plan including SQLite/native RSS and WAL storage.
- Review and approve the design before wiring the archive into live mutation.

Tests not executed: physical power cuts, disk corruption/failure, Windows/macOS
durability, or GitHub CI for the unpublished combined branch. The combined branch
was executed locally on both requested Python versions. No 3D renderer/physics
was introduced or tested.
