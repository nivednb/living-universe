"""Strict JSON shape validation before lossy list-to-set/dict reconstruction."""
from invariants import integer, require
import math


def validate_shape(state):
    def text(x):
        require(isinstance(x, str), "Expected checkpoint string")

    def number(x):
        require(integer(x), "Expected checkpoint integer")

    def boolean(x):
        require(type(x) is bool, "Expected checkpoint boolean")

    def array(check, unique=False):
        def run(items):
            require(isinstance(items, (list, tuple)), "Expected checkpoint array")
            for item in items:
                check(item)
            if unique:
                require(len({repr(x) for x in items}) == len(items), "Duplicate checkpoint set member")
        return run

    def row(*checks):
        def run(items):
            require(isinstance(items, (list, tuple)) and len(items) == len(checks), "Invalid checkpoint row")
            for check, item in zip(checks, items):
                check(item)
        return run

    def mapping(key_check, value_check):
        def run(items):
            require(isinstance(items, dict), "Expected checkpoint object")
            for key, value in items.items():
                key_check(key)
                value_check(value)
        return run

    def actor_key(key):
        require(isinstance(key, str) and key.isascii() and key.isdigit() and str(int(key)) == key,
                "Noncanonical character map key")

    texts = array(text, unique=True)
    actors = array(number, unique=True)
    resources = mapping(text, number)
    rows = {
        "settlements": row(text, text, resources, actors),
        "routes": row(text, text, number, number, number),
        "border_history": row(number, text, text, boolean, text),
        "travelers": row(number, text, number, number, number, array(row(text, text), unique=True)),
        "researchers": row(number, texts, resources),
        "techniques": row(text, texts, texts, number),
        "discoveries": row(number, text, texts),
        "pending": row(number, number, text, number, text),
        "events": row(text, number, text, actors),
        "claims": row(text, text, text, text),
        "world_claims": row(text, text, text, texts),
        "outcomes": row(number, number, text, boolean, number, number),
    }
    schema = {key: array(check) for key, check in rows.items()}
    schema.update({key: number for key in ("version", "rules_version", "seed", "day", "sequence")})
    schema.update({"destiny": mapping(actor_key, number), "locations": mapping(actor_key, text),
                   "transit": actors, "destinations": mapping(actor_key, text),
                   "history_knowledge": mapping(actor_key, texts), "beliefs": mapping(actor_key, texts)})
    require(isinstance(state, dict) and set(state) == set(schema) | {"rng"}, "Invalid checkpoint fields")
    for key, check in schema.items():
        check(state[key])
    # Python's Random.setstate performs the remaining generator-specific checks.
    row(number, array(number), lambda x: require(x is None or (type(x) in (int, float) and math.isfinite(x)),
                                               "Invalid Gaussian RNG cache"))(state["rng"])
    require(state["rng"][0] == 3 and len(state["rng"][1]) == 625
            and all(integer(x, 0, 2**32 - 1) for x in state["rng"][1][:-1])
            and integer(state["rng"][1][-1], 0, 624), "Invalid RNG state")
    for key in ("settlements", "travelers", "researchers", "techniques", "events", "claims", "world_claims"):
        identifiers = [item[0] for item in state[key]]
        require(len(set(identifiers)) == len(identifiers), "Duplicate " + key + " identifier")
    routes = [(item[0], item[1]) for item in state["routes"]]
    require(len(set(routes)) == len(routes), "Duplicate route")
