"""Independent bounded archive observation without simulation mutations."""
import tempfile
import unittest
from pathlib import Path
from historical_window import HistoricalEventWindow
from sqlite_history import SQLiteHistoryLedger


class HistoricalWindowTests(unittest.TestCase):
    def test_independent_windows_and_eviction(self):
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                ledger.append_many((i, i, "event", i % 3, {"value": i}) for i in range(20))
                a = HistoricalEventWindow(ledger, max_cached_events=3)
                b = HistoricalEventWindow(ledger, max_cached_events=2)
                self.assertEqual([r[0] for r in a.events(0, 10, limit=3)], [0, 1, 2])
                self.assertEqual([r[0] for r in b.events(10, 19, limit=2)], [10, 11])
                self.assertEqual([r[0] for r in a.events(17, 19, limit=3)], [17, 18, 19])
                self.assertEqual(a.cached_events, 3)
                self.assertEqual(b.cached_events, 2)
                self.assertEqual(ledger.cursor(), (19, 20))

    def test_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            with SQLiteHistoryLedger(Path(directory) / "history.sqlite") as ledger:
                with self.assertRaises(ValueError):
                    HistoricalEventWindow(ledger, 0)
                view = HistoricalEventWindow(ledger, 2)
                for args in ((-1, 5), (5, 1)):
                    with self.assertRaises(ValueError):
                        view.events(*args)
                with self.assertRaises(ValueError):
                    view.events(0, 5, limit=3)


if __name__ == "__main__":
    unittest.main()
