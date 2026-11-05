"""Read-only, bounded historical event windows for archive browsing.

This is not historical *world-state* reconstruction: the existing history log
contains descriptions rather than causal state transitions.
"""
from collections import OrderedDict


class HistoricalEventWindow:
    def __init__(self, ledger, max_cached_events=512):
        if type(max_cached_events) is not int or max_cached_events < 1:
            raise ValueError("max_cached_events must be positive")
        self.ledger = ledger
        self.max_cached_events = max_cached_events
        self._cache = OrderedDict()

    def events(self, start_day, end_day, *, actor=None, limit=256):
        """Return up to `limit` events in a window, using bounded memory.

        A list is intentional: caller-visible memory is bounded by `limit`.
        This class caches only the last `max_cached_events` event records.
        """
        if (type(start_day) is not int or type(end_day) is not int or
                start_day > end_day or start_day < 0):
            raise ValueError("invalid time window")
        if type(limit) is not int or limit < 1 or limit > self.max_cached_events:
            raise ValueError("limit must be positive and within cache budget")
        if actor is not None and type(actor) is not int:
            raise ValueError("actor must be an integer")
        result = []
        for record in self.ledger.iter_events(start_day=start_day, end_day=end_day,
                                               actor=actor, batch_size=min(limit, 256)):
            result.append(record)
            key = record[0]
            self._cache[key] = record
            self._cache.move_to_end(key)
            if len(self._cache) > self.max_cached_events:
                self._cache.popitem(last=False)
            if len(result) == limit:
                break
        return result

    @property
    def cached_events(self):
        return len(self._cache)

    def clear(self):
        self._cache.clear()
