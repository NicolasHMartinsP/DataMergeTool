from dataclasses import dataclass, field
from typing import Optional, Dict

@dataclass
class Entity:
    id: str
    name: str
    contact: Optional[str] = None
    pix: Optional[str] = None
    target_id: Optional[str] = None
    transactions_count: int = 0
    transactions_by_store: Dict[str, int] = field(default_factory=dict)