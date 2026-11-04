"""Scheduled discoveries with individual historical witnesses and controlled teaching.

A small integrated vertical slice, not yet part of the authoritative Universe.
"""
from dataclasses import dataclass
import heapq
from discovery import DiscoveryWorld
from history import Event, HistoricalLedger

@dataclass(frozen=True)
class ResearchJob:
    researcher_id: int
    technique_id: str
    completion_day: int

class ResearchSimulation:
    def __init__(self, discoveries: DiscoveryWorld, ledger: HistoricalLedger):
        self.discoveries = discoveries
        self.ledger = ledger
        self.day = 0
        self.sequence = 0
        self.jobs: dict[int, ResearchJob] = {}
        self.queue: list[tuple[int, int]] = []
        self.outcomes: list[tuple[int, int, str, bool]] = []

    def schedule(self, researcher_id: int, technique_id: str, duration: int):
        if not isinstance(duration, int) or duration <= 0:
            raise ValueError("Research duration must be a positive integer")
        if researcher_id in self.jobs:
            raise ValueError("Researcher is already occupied")
        researcher = self.discoveries.researchers[researcher_id]
        technique = self.discoveries.techniques[technique_id]
        if technique_id in researcher.knowledge:
            raise ValueError("Technique already known")
        if not technique.prerequisites.issubset(researcher.knowledge):
            raise ValueError("Research prerequisites not met")
        job = ResearchJob(researcher_id, technique_id, self.day + duration)
        self.jobs[researcher_id] = job
        heapq.heappush(self.queue, (job.completion_day, researcher_id))
        return job

    def advance(self, days: int):
        if not isinstance(days, int) or days < 0:
            raise ValueError("Days must be nonnegative")
        end = self.day + days
        while self.queue and self.queue[0][0] <= end:
            when, researcher_id = heapq.heappop(self.queue)
            job = self.jobs.pop(researcher_id)
            succeeded = self.discoveries.discover(researcher_id, job.technique_id)
            self.outcomes.append((when, researcher_id, job.technique_id, succeeded))
            event_id = f"research-{self.sequence}"
            self.sequence += 1
            outcome = "discovered" if succeeded else "failed to discover"
            self.ledger.record(Event(event_id, when, f"Agent {researcher_id} {outcome} {job.technique_id}", frozenset({researcher_id})))
        self.day = end

    def teach(self, teacher_id: int, student_id: int, technique_id: str):
        if self.discoveries.teach(teacher_id, student_id, technique_id):
            event_id = f"research-{self.sequence}"
            self.sequence += 1
            self.ledger.record(Event(event_id, self.day, f"Agent {teacher_id} taught {technique_id} to {student_id}", frozenset({teacher_id, student_id})))
            return True
        return False
