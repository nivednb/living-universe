"""Regressions for checkpoint trust boundaries and deterministic integration."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from borders import Route, Traveler
from discovery import Researcher, Technique
from history import Claim, Event
from unified_persistence import decode, encode, load, save
from world_state import KnowledgeClaim
from test_unified_persistence import make_world


class FoundationTests(unittest.TestCase):
    def test_teaching_during_research_does_not_rediscover(self):
        world = make_world()
        # Seed 1 would have succeeded before the fix (roll 17, chance 60).
        world.rng.seed(1)
        world.research(2, "qi", 1)
        self.assertTrue(world.teach(1, 2, "qi"))
        restored = decode(encode(world))
        world.advance(1)
        restored.advance(1)
        self.assertFalse(world.outcomes[-1][3])
        self.assertEqual(world.outcomes[-1][4], 17)
        self.assertEqual(world.discovery.discoveries, [])
        self.assertEqual(world.digest(), restored.digest())
        self.assertTrue(world.history.knows(2, "kernel-1"))

    def test_simultaneous_events_keep_sequence_across_restore(self):
        world = make_world()
        world.depart(1, "market")
        world.research(1, "hybrid", 5)
        world.research(2, "qi", 5)
        restored = decode(encode(world))
        world.advance(5)
        restored.advance(4)
        restored.advance(1)
        self.assertEqual(world.digest(), restored.digest())
        events = list(world.history.events.values())[-3:]
        self.assertEqual([e.description.split(":")[0] for e in events][0], "arrival")
        self.assertEqual([o[1] for o in world.outcomes], [1, 2])
        world.validate()

    def test_history_and_beliefs_roundtrip_without_global_knowledge(self):
        world = make_world()
        world.history.record(Event("ancient", -100, "An uncertain encounter", frozenset({1})))
        world.history.publish_claim(Claim("rumor", "ancient", "A disputed account", "archive"))
        world.history.communicate("rumor", 2)
        world.state.add_claim(KnowledgeClaim("belief", "Maybe", "ancient", ("rumor",)))
        world.state.learn(2, "belief")
        restored = decode(encode(world))
        self.assertTrue(restored.history.knows(1, "ancient"))
        self.assertFalse(restored.history.knows(2, "ancient"))
        self.assertTrue(restored.history.knows(2, "rumor"))
        self.assertNotIn(1, restored.state.beliefs)
        self.assertEqual(world.digest(), restored.digest())

    def test_provenance_success_is_not_conditional(self):
        world = make_world()
        world.rng.seed(1)
        world.research(1, "hybrid", 1)
        world.advance(1)
        self.assertTrue(world.outcomes[0][3])
        self.assertEqual(world.discovery.discoveries[0].source_knowledge, ("math", "qi"))
        self.assertEqual(world.digest(), decode(encode(world)).digest())

    def test_corruption_matrix(self):
        world = make_world()
        world.depart(1, "market")
        world.research(1, "hybrid", 5)
        world.history.publish_claim(Claim("rumor", "kernel-0", "Maybe", "archive"))
        world.history.communicate("rumor", 2)
        world.state.add_claim(KnowledgeClaim("belief", "Maybe", "kernel-0", ("rumor",)))
        world.state.learn(2, "belief")
        base = encode(world)

        def duplicate_arrival(s):
            s["pending"].append([5, s["sequence"], "arrival", 1, "market"])
            s["sequence"] += 1

        mutations = {
            "duplicate arrival": duplicate_arrival,
            "unknown destination": lambda s: (s["destinations"].update({"1": "missing"}), s["pending"][0].__setitem__(4, "missing")),
            "missing field": lambda s: s.pop("rng"),
            "unknown field": lambda s: s.update({"future": 1}),
            "bool version": lambda s: s.update({"version": True}),
            "old rules": lambda s: s.update({"rules_version": 1}),
            "bool rules": lambda s: s.update({"rules_version": True}),
            "negative day": lambda s: s.update({"day": -1}),
            "fractional day": lambda s: s.update({"day": 0.5}),
            "negative sequence": lambda s: s.update({"sequence": -1}),
            "fractional arrival": lambda s: s["pending"][0].__setitem__(0, 5.5),
            "negative sequence entry": lambda s: s["pending"][0].__setitem__(1, -1),
            "bool actor": lambda s: s["pending"][0].__setitem__(3, True),
            "unknown actor": lambda s: s["pending"][0].__setitem__(3, 999),
            "unknown event kind": lambda s: s["pending"][0].__setitem__(2, "magic"),
            "bad pending shape": lambda s: s["pending"].append([1]),
            "unknown technique": lambda s: s["pending"][1].__setitem__(4, "missing"),
            "lost prerequisites": lambda s: s["researchers"][0][1].remove("math"),
            "duplicate researcher": lambda s: s["researchers"].append(s["researchers"][0]),
            "duplicate resident": lambda s: s["settlements"][0][3].append(2),
            "duplicate claim": lambda s: s["claims"].append(s["claims"][0]),
            "duplicate world claim": lambda s: s["world_claims"].append(s["world_claims"][0]),
            "unknown historical claim event": lambda s: s["claims"][0].__setitem__(1, "missing"),
            "unknown historical knowledge": lambda s: s["history_knowledge"]["2"].append("missing"),
            "omniscient memory": lambda s: s["history_knowledge"]["2"].append("kernel-0"),
            "lost witness memory": lambda s: s["history_knowledge"]["1"].clear(),
            "unknown witness": lambda s: s["events"][0][3].append(999),
            "future event": lambda s: s["events"][0].__setitem__(1, 100),
            "unknown belief": lambda s: s["beliefs"]["2"].append("missing"),
            "unknown believer": lambda s: s["beliefs"].update({"999": ["belief"]}),
            "unknown world claim event": lambda s: s["world_claims"][0].__setitem__(2, "missing"),
            "unknown evidence": lambda s: s["world_claims"][0][3].append("missing"),
            "invalid destiny": lambda s: s["destiny"].update({"1": 101}),
            "aliased character map key": lambda s: s["destiny"].update({"01": 20}),
            "invalid RNG": lambda s: s["rng"][1].__setitem__(0, -1),
            "truncated RNG": lambda s: s["rng"][1].pop(),
            "negative supplies": lambda s: s["travelers"][0].__setitem__(2, -1),
            "negative expertise": lambda s: s["researchers"][0][2].update({"science": -1}),
            "unknown knowledge": lambda s: s["researchers"][0][1].append("missing"),
            "unknown prerequisite": lambda s: s["techniques"][0][2].append("missing"),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                state = copy.deepcopy(base)
                mutate(state)
                with self.assertRaises(ValueError):
                    decode(state)
        for malformed in (None, [], {}, "world"):
            with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                decode(malformed)

    def test_discovery_corruption(self):
        world = make_world()
        world.rng.seed(1)
        world.research(1, "hybrid", 1)
        world.advance(1)
        base = encode(world)
        mutations = [lambda s: s["discoveries"][0].__setitem__(2, ["math"]),
                     lambda s: s["discoveries"].append(s["discoveries"][0]),
                     lambda s: s["researchers"][0][1].remove("hybrid"),
                     lambda s: s["discoveries"].clear()]
        for mutate in mutations:
            state = copy.deepcopy(base)
            mutate(state)
            with self.assertRaises(ValueError):
                decode(state)

    def test_interrupted_save_preserves_previous_checkpoint(self):
        for target in ("unified_persistence.os.fsync", "unified_persistence.Path.replace",
                       "unified_persistence.json.dump"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "world.json"
                world = make_world()
                save(world, path)
                before = path.read_bytes()
                world.research(1, "hybrid", 3)
                def interrupted_dump(state, stream, **kwargs):
                    stream.write('{"partial":')
                    raise OSError("interrupted write")

                failure = interrupted_dump if target.endswith("json.dump") else OSError("injected interruption")
                with patch(target, side_effect=failure):
                    with self.assertRaises(OSError):
                        save(world, path)
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(load(path).day, 0)
                self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_failed_first_save_and_invalid_live_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            with patch("unified_persistence.Path.replace", side_effect=OSError("interrupted")):
                with self.assertRaises(OSError):
                    save(make_world(), path)
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(directory).iterdir()), [])
            world = make_world()
            save(world, path)
            before = path.read_bytes()
            world.state.settlements["sect"].residents.clear()
            with self.assertRaises(ValueError):
                save(world, path)
            self.assertEqual(path.read_bytes(), before)

    def test_unique_temporary_file_and_abandoned_file_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            abandoned = path.with_suffix(".json.tmp")
            abandoned.write_text("interrupted earlier save")
            save(make_world(), path)
            self.assertEqual(load(path).day, 0)
            self.assertEqual(abandoned.read_text(), "interrupted earlier save")

    def test_process_exit_before_replace_preserves_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            world = make_world()
            save(world, path)
            before = path.read_bytes()
            script = ("import os,sys; from pathlib import Path; from unittest.mock import patch; "
                      "from unified_persistence import load,save; "
                      "w=load(sys.argv[1]); w.advance(1); "
                      "p=patch.object(Path,'replace',lambda *a: os._exit(73)); p.start(); "
                      "save(w,sys.argv[1])")
            process = subprocess.run([sys.executable, "-c", script, str(path)], check=False)
            self.assertEqual(process.returncode, 73)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(len(list(Path(directory).glob("*.tmp"))), 1)
            save(world, path)
            self.assertEqual(load(path).digest(), world.digest())

    def test_pending_research_index_restores_and_clears(self):
        world = make_world()
        world.rng.seed(0)  # roll 49 exceeds actor 2's qi chance (30).
        world.research(2, "qi", 1)
        world = decode(encode(world))
        with self.assertRaises(ValueError):
            world.research(2, "qi", 1)
        world.advance(1)
        self.assertFalse(world.outcomes[-1][3])
        world.research(2, "qi", 1)
        world.validate()

    def test_invalid_json_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            valid = json.dumps(encode(make_world()))
            for data in (valid[:100], '{"version":1,"version":1}',
                         valid.replace('"day": 0', '"day": NaN'),
                         valid.replace('"food": 30', '"food": 30, "food": 30')):
                path.write_text(data)
                with self.assertRaises(ValueError):
                    load(path)

    def test_invalid_durations_are_atomic(self):
        for duration in (True, False, 1.5, "1", None, -1):
            world = make_world()
            before = world.digest()
            with self.assertRaises(ValueError):
                world.advance(duration)
            with self.assertRaises(ValueError):
                world.research(1, "hybrid", duration)
            self.assertEqual(world.digest(), before)

    def test_invalid_route_time_rejected(self):
        for duration in (True, 1.5, 0, -1):
            with self.assertRaises(ValueError):
                Route("magic", "science", duration)

    def test_history_names_do_not_collide(self):
        world = make_world()
        world.history.record(Event("kernel-1", -1, "Prehistory", frozenset({1})))
        world.research(1, "hybrid", 1)
        world.advance(1)
        world.validate()
        with self.assertRaises(ValueError):
            world.history.publish_claim(Claim("kernel-1", "kernel-1", "Ambiguous", "archive"))

    def test_hash_seed_independence(self):
        import os
        script = ("from test_unified_persistence import make_world; "
                  "w=make_world(); w.depart(1,'market'); w.research(1,'hybrid',5); "
                  "w.advance(10); print(w.digest())")
        outputs = []
        for seed in ("1", "123", "random"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            env["PYTHONPATH"] = str(Path(__file__).resolve().parent)
            outputs.append(subprocess.check_output([sys.executable, "-c", script], env=env, text=True))
        self.assertEqual(len(set(outputs)), 1)

    def test_long_deterministic_checkpoint_continuation(self):
        from benchmark_unified import build, schedule
        for seed in (0, 42, 8675309):
            with self.subTest(seed=seed):
                reference, resumed = build(20, seed), build(20, seed)
                for iteration in range(100):
                    schedule(reference, iteration)
                    schedule(resumed, iteration)
                    reference.advance(10)
                    resumed.advance(3)
                    if iteration % 10 == 0:
                        resumed = decode(encode(resumed))
                    resumed.advance(7)
                    reference.validate()
                    resumed.validate()
                self.assertEqual(reference.digest(), resumed.digest())

    def test_rules_v2_golden_checkpoint_digest(self):
        from benchmark_unified import build, schedule
        world = build(20, 42)
        for iteration in range(5):
            schedule(world, iteration)
            world.advance(10 if iteration < 4 else 3)
        self.assertEqual(world.RULES_VERSION, 2)
        self.assertEqual(world.digest(), "dd4d13c358216e612383655f5aee38e3acc40d94172e9a08e0990ce5baba5193")

    def test_gaussian_rng_cache_roundtrip(self):
        world = make_world()
        world.rng.gauss(0, 1)
        restored = decode(encode(world))
        self.assertEqual(world.rng.gauss(0, 1), restored.rng.gauss(0, 1))
        self.assertEqual(world.digest(), restored.digest())


if __name__ == "__main__":
    unittest.main()
