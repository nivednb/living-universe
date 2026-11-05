# Viewer-independent projections and future 3D clients

`prototype/views.py` defines version-1 read models over the unified kernel. This
implements a renderer boundary, not a renderer, network service or spatial engine.
The kernel remains usable headlessly with Python's standard library.

## Authority and clock

The simulation host issues commands and advances simulation days. Renderers read
detached views. Reading, reconnecting, choosing an actor, hiding a tab or changing
camera position never advances time, draws randomness or changes pending events.
The same commanded run produces the same checkpoint digest with zero, one or
multiple viewers. An actual host process is still required to run the simulation;
there is no background service or wall-clock catch-up implementation yet.

No frame delta, camera distance, visible-object list, display refresh rate or
renderer physics result belongs in `UnifiedKernel.advance`. If later simulation
levels of detail are introduced, their resolution must follow authoritative
world rules and causal relevance, independently of observer attention.

## Contracts and disclosure

| Entry point | Contents | Intended caller |
| --- | --- | --- |
| `observer_view(world, actor_ids=None)` | Settlements, resources, residents, selected actors and route topology | Authorized observer/research host |
| `character_view(world, actor)` | Self location/travel, acquired technique IDs, witnessed memories, received claims and beliefs | Host acting for an authorized character |
| `to_wire(view)` | Fresh JSON-compatible object with `version`, `scope` and simulation `day` | 2D/3D adapters, recording or transport layer |

Observer actor selection filters actor records only. Settlements still contain
all residents, and all routes remain present. Selection is a rendering convenience,
not a visibility or access-control mechanism. **Never use an observer view as a
character response.** This library performs no authentication: a server must bind
the actor ID to its authenticated principal and authorize privileged observers.

Character views do not include other actors or globally available techniques,
routes, events or resources. There is no proximity/perception model yet. A rumor
does not disclose its underlying event's actual description, witnesses or private
evidence. Beliefs disclose their propositions without disclosing hidden evidence.
These are disclosure boundaries over existing knowledge, not a complete model of
human memory, perception, lie detection or what an actor infers from a statement.

Neither wire scope includes hidden destiny, the random stream, research rolls,
pending research jobs or checkpoint internals. Authoritative checkpoints remain
privileged persistence data. Views are not restorable checkpoints or replay logs.
Public fields deliberately omit data a future renderer does not need.

Frozen dataclasses and nested tuples prevent accidental view mutation. All values
are copied from the world; later world changes do not update old views. `to_wire`
returns a fresh mutable JSON object whose mutation also cannot affect the kernel.
Collections have stable order. New visual-only fields can evolve the view schema
without changing simulation rules or checkpoint schema. Breaking contract changes
require a new view version. This step leaves rules at 2 and checkpoint schema at 1.

Frozen dataclasses are not a Python sandbox: arbitrary Python code can bypass
assignment guards with `object.__setattr__` or `__dict__`. Such edits affect only
the detached object. Untrusted clients should receive serialized messages, not
Python kernel or archive handles; host authentication/authorization remains
required. Regression tests explicitly exercise these bypasses without changing
authoritative state.

## Space and future 3D

The implemented spatial model is a region/settlement graph, with directed region
routes and scheduled settlement arrivals. Actor IDs, settlement IDs and region IDs
are world identifiers, not scene node identifiers. During transit, `region` is the
last region occupied; `settlement_id` is null, and `destination_id` / `arrival_day`
describe the committed journey. Arrival clears those transit fields.

A 2D adapter may draw a map and a 3D adapter may place graph nodes in a scene. Those
layouts are presentation only: interpolating a journey or moving a camera cannot
change authoritative location, travel duration, resources or discoveries. There
are currently no world coordinates, altitude, terrain, collision or line-of-sight
mechanics. Inventing renderer coordinates must not imply these are simulated.

When gameplay needs real spatial distances or verticality, introduce an explicit
authoritative spatial contract: documented coordinate frame, units, precision,
positions, topology and deterministic queries. Include all mechanics-relevant
spatial state in checkpoints and invariant tests; bump simulation rules if the
behavior changes. A 2D client can then project that same state onto a plane while
a 3D client uses all supported dimensions. Neither client should become the
source of world truth. No rendering framework or physics library is selected here.

## Validation and limits

Run `cd prototype && python -m unittest discover -s tests -v`. View tests cover
headless-versus-observed continuation, viewer selection, immutable/detached data,
knowledge isolation, rumor/evidence boundaries, missing checkpoint secrets,
authoritative arrival timing, JSON encoding and checkpoint-roundtrip equality.
The existing rules-v2 golden checkpoint test also remains unchanged.

`test_view_archive_integration.py` runs four compatibility checks when the PR3
archive modules are installed alongside these views. On the standalone viewer
branch they are explicitly skipped, rather than importing an unmerged dependency.
The combined audit checkout runs all four: archive-backed memories and rumors,
immutable historical observation, verified checkpoint restore, view equality and
deterministic continuation. The archive event mapping is temporarily substituted
only in a host-controlled test scope and restored before simulation advances.

Reads assume a valid kernel and must be serialized with host mutation, or operate
on a host-owned consistent snapshot. There is no thread safety or transaction
layer. Observer reads allocate the projected world; character memories scale
with that character's known history. Arrival lookup scans pending events. High
viewer counts will need bounded queries, indexing and caching outside simulation
mutation; viewer filters must never suppress world events. There are no deltas,
subscriptions, network transport, command authorization, UI or frame benchmarks
in this increment.
