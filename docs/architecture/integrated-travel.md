# Integrated travel vertical slice

`prototype/travel_simulation.py` connects the previously separate border, settlement and historical ledger prototypes.

- Travelers depart from a settlement only when route knowledge, supplies, hazard and clearance permit.
- Travel consumes supplies and schedules an arrival at a later simulation day.
- A traveler in transit is not resident at either endpoint.
- Departure and arrival become historical events, initially witnessed by the traveler alone.
- Failed departure leaves settlement membership unchanged.

Run from `prototype/`: `python -m unittest discover -s tests -v`.

**Limitations:** This is not integrated into `prototype/sim.py` or its persistence format. Journeys cannot yet be saved/restored, intercepted or rerouted; no event-level policy enforcement, travel accidents, communication or autonomous decision-making is modeled. Travel event IDs are local to this subsystem and need namespacing when merged with other ledgers.
