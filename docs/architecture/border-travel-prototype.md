# Border travel prototype

The standalone `prototype/borders.py` models directional travel routes, route discovery, supplies, restrictions and hazards. An agent cannot travel along a route it has not learned, cannot cross a route that does not exist, and cannot travel without sufficient supplies. Successful travel consumes supplies and changes the agent's region.

**Limitations:** Travel currently resolves instantly in simulation time; `travel_days` is only a supply cost and returned duration. Navigation and clearance are fixed thresholds, not probabilistic risk, institutional decisions or social relationships. This is not integrated with the main event scheduler, historical ledger, settlements, or persistence. The route model does not yet represent paths through intermediate regions, attempts to evade restrictions, or changing policies.

Next: schedule departures and arrivals, add explicit travel events to the historical ledger, route discoveries via evidence, and institution-specific border enforcement.
