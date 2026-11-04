# Reference simulation prototype (Python standard library)

This is a small, tested **reference scheduler**, not the production engine or a functioning RPG. It deliberately has no rendering dependency and is designed to inform a later Rust implementation.

Run from this directory:
```sh
python sim.py --agents 10000 --days 365
python -m unittest discover -s tests
```

Models five starting cultures, deterministic scheduled study/training/migration events, persistent identities, a basic event list and a digest. It does **not** yet implement physical fields, institutions, knowledge provenance, replay restoration, save/load, ecology, mortality, AI or 2D/3D views. The RNG representation in snapshots is diagnostic, not a stable persistence format.

Local baseline on 2026-11-04: 10,000 agents, 365 days, 232,625 events, 1.27 seconds elapsed, 141,964 KB peak resident memory (single container run). Four unit tests passed. This measures a very simple synthetic workload, **not** the target civilization simulation.
