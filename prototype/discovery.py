"""Deterministic interdisciplinary discovery and knowledge transmission.

Standalone reference model. Integration into the persistent event scheduler is pending.
"""
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Technique:
    id: str
    traditions: frozenset[str]
    prerequisites: frozenset[str] = frozenset()
    difficulty: int = 0

    def __post_init__(self):
        if not self.id or not self.traditions or self.difficulty < 0:
            raise ValueError("Invalid technique")

@dataclass
class Researcher:
    id: int
    knowledge: set[str] = field(default_factory=set)
    expertise: dict[str, int] = field(default_factory=dict)

@dataclass(frozen=True)
class Discovery:
    researcher_id: int
    technique_id: str
    source_knowledge: tuple[str, ...]

class DiscoveryWorld:
    def __init__(self):
        self.techniques: dict[str, Technique] = {}
        self.researchers: dict[int, Researcher] = {}
        self.discoveries: list[Discovery] = []

    def add_technique(self, technique: Technique):
        if technique.id in self.techniques:
            raise ValueError("Duplicate technique")
        self.techniques[technique.id] = technique

    def add_researcher(self, researcher: Researcher):
        if researcher.id in self.researchers:
            raise ValueError("Duplicate researcher")
        self.researchers[researcher.id] = researcher

    def discover(self, researcher_id: int, technique_id: str):
        researcher = self.researchers[researcher_id]
        technique = self.techniques[technique_id]
        if technique_id in researcher.knowledge:
            return False
        if not technique.prerequisites.issubset(researcher.knowledge):
            return False
        if sum(researcher.expertise.get(t, 0) for t in technique.traditions) < technique.difficulty:
            return False
        researcher.knowledge.add(technique_id)
        self.discoveries.append(Discovery(researcher_id, technique_id, tuple(sorted(technique.prerequisites))))
        return True

    def teach(self, teacher_id: int, student_id: int, technique_id: str):
        teacher = self.researchers[teacher_id]
        student = self.researchers[student_id]
        if technique_id not in self.techniques or technique_id not in teacher.knowledge:
            return False
        if technique_id in student.knowledge:
            return False
        student.knowledge.add(technique_id)
        return True
