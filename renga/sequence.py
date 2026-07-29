"""Data model for a renga sequence: a list of verses with provenance metadata.

Kept as plain dataclasses with to_dict/from_dict rather than pydantic etc.
because the only consumers are json.dump and numpy/scipy in metrics.py --
no validation layer needed beyond what the scribe already does.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional
import numpy as np


@dataclass
class Verse:
    index: int
    author: str  # "human" | "model_A" | "model_B" (persona names double as rotation identity)
    text: str
    motifs: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    rejections: List[str] = field(default_factory=list)  # reasons candidates were bounced
    unresolved_violation: bool = False  # accepted past max_retries despite a failing check
    embedding: Optional[list] = None  # stored as plain list for JSON; cast to np.array on use

    def emb(self) -> np.ndarray:
        return np.array(self.embedding, dtype=float)

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d):
        return Verse(**d)


@dataclass
class Sequence:
    condition: str
    seed_id: str
    verses: List[Verse] = field(default_factory=list)

    def to_dict(self):
        return {"condition": self.condition, "seed_id": self.seed_id, "verses": [v.to_dict() for v in self.verses]}

    @staticmethod
    def from_dict(d):
        return Sequence(condition=d["condition"], seed_id=d["seed_id"], verses=[Verse.from_dict(v) for v in d["verses"]])
