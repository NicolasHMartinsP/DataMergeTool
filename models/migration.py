from dataclasses import dataclass

@dataclass
class Migration:
    source_id: str
    target_id: str
    transactions_count: int