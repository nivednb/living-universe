import tempfile
import unittest
from pathlib import Path
from sim import Universe
from persistence import save, load

class CheckpointTests(unittest.TestCase):
    def test_resume_matches_uninterrupted_run(self):
        baseline = Universe(100, 42)
        baseline.advance(365)
        paused = Universe(100, 42)
        paused.advance(120)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            save(paused, path)
            resumed = load(path)
            resumed.advance(245)
        self.assertEqual(resumed.digest(), baseline.digest())
    def test_unknown_schema_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            save(Universe(2), path)
            import json
            state = json.loads(path.read_text())
            state["schema_version"] = 999
            path.write_text(json.dumps(state))
            with self.assertRaises(ValueError):
                load(path)

if __name__ == "__main__":
    unittest.main()
