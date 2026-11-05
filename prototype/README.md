# Reference simulation prototypes (Python standard library)

These renderer-independent Python models explore deterministic scheduling and
world invariants. They are not a playable game or a production civilization engine.
Python 3.12+ is the supported reference environment; no pip packages are required.

From the repository root:
```sh
python3 -m venv .venv
cd prototype
../.venv/bin/python -m unittest discover -s tests -v
../.venv/bin/python benchmark_unified.py --agents 1000 --rounds 100
```

`unified_kernel.py` integrates one clock, scheduled travel/research, settlement
residency, bounded hidden destiny, discovery provenance, teaching, historical
witnesses and claims. `unified_persistence.py` saves and restores complete JSON
checkpoints with schema and simulation-rule version gates. `world.validate()`
checks consistency without consuming randomness. Saves and snapshots validate
before encoding; restores validate both JSON shape and reconstructed invariants.
See [the stability report](../docs/architecture/foundation-stability.md) for
verified results, compatibility policy, benchmark methodology and limitations.

`views.py` provides immutable observer and character read models plus JSON wire
messages. Reading views never advances the world. They expose the current
region/route graph to future 2D or 3D adapters without committing to a renderer.
Character views disclose only self state and acquired knowledge; observer access
is privileged. See [the view contract](../docs/architecture/view-contract.md) for
authorization requirements, spatial semantics and remaining limits.

The older `sim.py`, `travel_simulation.py` and `research_simulation.py` remain
separate reference experiments, with their own tests. Legacy `sim.py` checkpoint
files are not interchangeable with unified checkpoints. `sim.py --agents 10000
--days 365` measures a different, simpler workload; do not compare it directly
with the integrated benchmark.

The prototype has no autonomous planning, ecology, institutions, mortality,
network server, renderer or full cosmological fate model. Historical descriptions
are strings, not a durable typed replay log. No third-party source or paid
services were added. Source-code licensing is still unresolved in the repository;
`LICENSE-DOCS` covers documentation only.
