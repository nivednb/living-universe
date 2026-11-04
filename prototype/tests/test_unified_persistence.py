import tempfile
import unittest
from pathlib import Path
from borders import Route, Traveler
from discovery import Researcher, Technique
from world_state import Settlement
from unified_kernel import UnifiedKernel
from unified_persistence import save, load, encode, decode

def make_world():
    w = UnifiedKernel(8675309)
    w.add_settlement(Settlement("sect", "cultivation", {"food": 30}))
    w.add_settlement(Settlement("market", "nexus", {"food": 7}))
    w.add_route(Route("cultivation", "nexus", 5, 10, 20))
    w.add_technique(Technique("math", frozenset({"science"}), difficulty=1))
    w.add_technique(Technique("qi", frozenset({"cultivation"}), difficulty=1))
    w.add_technique(Technique("hybrid", frozenset({"science","cultivation"}), frozenset({"math","qi"}), 8))
    w.add_character(Traveler(1,"cultivation",20,80,60,{("cultivation","nexus")}),
                    Researcher(1,{"math","qi"},{"science":5,"cultivation":4}),"sect",20)
    w.add_character(Traveler(2,"cultivation",20,80,60,{("cultivation","nexus")}),
                    Researcher(2,{"math"},{"science":3}),"sect",-20)
    return w

class UnifiedPersistenceTests(unittest.TestCase):
    def test_roundtrip_inflight_and_pending_research(self):
        w = make_world()
        w.depart(1,"market")
        w.research(1,"hybrid",3)
        w.advance(2)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"world.json"
            save(w,path)
            restored = load(path)
            self.assertEqual(encode(w),encode(restored))
            w.advance(10)
            restored.advance(10)
            self.assertEqual(encode(w),encode(restored))
            self.assertEqual(w.digest(),restored.digest())

    def test_repeated_checkpoints_preserve_rng(self):
        w = make_world()
        w.research(1,"hybrid",1)
        w.advance(1)
        copy = decode(encode(w))
        self.assertEqual(w.rng.getstate(),copy.rng.getstate())
        self.assertEqual(w.history.knowledge,copy.history.knowledge)

    def test_rules_version_mismatch_rejected(self):
        state = encode(make_world())
        state["rules_version"] = 999
        with self.assertRaises(ValueError):
            decode(state)

    def test_discovery_provenance_survives_restore(self):
        w = make_world()
        w.research(1, "hybrid", 1)
        w.advance(1)
        if w.outcomes[-1][3]:
            self.assertEqual(len(w.discovery.discoveries), 1)
            self.assertEqual(w.discovery.discoveries[0].source_knowledge, ("math", "qi"))
        restored = decode(encode(w))
        self.assertEqual(encode(w), encode(restored))

    def test_rejects_duplicate_research_jobs(self):
        w = make_world()
        w.research(1, "hybrid", 3)
        state = encode(w)
        state["pending"].append([4, state["sequence"], "research", 1, "hybrid"])
        state["sequence"] += 1
        with self.assertRaises(ValueError):
            decode(state)

    def test_rejects_corrupt_residency(self):
        state = encode(make_world())
        state["settlements"][0][3].clear()
        with self.assertRaises(ValueError):
            decode(state)

    def test_rejects_schema_mismatch(self):
        state = encode(make_world())
        state["version"] = 999
        with self.assertRaises(ValueError):
            decode(state)

    def test_rejects_missing_arrival_event(self):
        w = make_world()
        w.depart(1, "market")
        state = encode(w)
        state["pending"].clear()
        with self.assertRaises(ValueError):
            decode(state)

    def test_rejects_corrupt_event_sequence(self):
        w = make_world()
        w.research(1, "hybrid", 3)
        state = encode(w)
        state["pending"][0][1] += 100
        with self.assertRaises(ValueError):
            decode(state)

    def test_rejects_region_residence_mismatch(self):
        state = encode(make_world())
        state["travelers"][0][1] = "science"
        with self.assertRaises(ValueError):
            decode(state)

    def test_rejects_invalid_pending_time(self):
        w = make_world()
        w.research(1,"hybrid",3)
        state = encode(w)
        state["pending"][0][0] = -1
        with self.assertRaises(ValueError):
            decode(state)

if __name__ == "__main__":
    unittest.main()
