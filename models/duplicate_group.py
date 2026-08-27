from dataclasses import dataclass, field
from typing import List
from models.entity import Entity

@dataclass
class DuplicateGroup:
    name: str
    master: Entity
    duplicates: List[Entity]
    reason: str = "Exact Match"
    pending_items: List[Entity] = field(default_factory=list)