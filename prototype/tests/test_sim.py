import unittest
from sim import Universe, REGIONS
class SimulationTests(unittest.TestCase):
    def test_reproducibility(self):
        a,b=Universe(100,42),Universe(100,42)
        a.advance(365); b.advance(365)
        self.assertEqual(a.digest(),b.digest())
    def test_event_order(self):
        w=Universe(100,5); w.advance(365)
        self.assertEqual([e[0] for e in w.events],sorted(e[0] for e in w.events))
    def test_all_cultures(self):
        self.assertEqual(set(a.region for a in Universe(50).agents.values()),set(REGIONS[:5]))
    def test_incremental(self):
        a,b=Universe(100,42),Universe(100,42)
        a.advance(100); a.advance(265); b.advance(365)
        self.assertEqual(a.digest(),b.digest())
if __name__=="__main__": unittest.main()
