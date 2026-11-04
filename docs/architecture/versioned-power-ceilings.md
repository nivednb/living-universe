# Versioned power ceilings and simulation fidelity

**Status:** First standalone reference implementation; not yet integrated into the main simulation.

Distinguish:
- **Lore capability:** A possible phenomenon in the fictional cosmology.
- **Actor capability:** What a particular being has earned, discovered or inherited.
- **Engine capability:** What the running software can simulate with defined rules.
- **Fidelity:** How accurately an event can be modeled, independent of its fictional magnitude.

`prototype/power_ceiling.py` contains a minimal versioned capability gate. Unsupported abilities are not executed; the gate reports them as abstract/unsupported. It does **not** actually simulate abstract interventions or queue them for future execution.

## Compatibility requirements
Engine upgrades must not silently change established actor abilities, retroactively rewrite history or make old saves invalid. Capability manifests should be versioned with checkpoints, and new effects must have deterministic, tested semantics. Replaying an old simulation should retain its historical rule version unless explicitly migrated.

## Scaling principle
Hardware upgrades may increase the number of active agents, spatial resolution, frequency of events or depth of causal modeling. They should not be mapped directly to character strength. A high-tier being can be represented abstractly until a validated higher-fidelity engine exists.

## Future work
Implement effect schemas, explicit cost and counterplay rules, abstract-event resolution, rule-version pinning, compatibility migrations, actor-specific growth, hierarchy and deterrence. Distinguish model fidelity from balance and world lore.
