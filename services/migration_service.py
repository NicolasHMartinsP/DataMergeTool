from typing import List
from models.entity import Entity
from models.migration import Migration

class MigrationService:
    def __init__(self):
        self.migrations: List[Migration] = []

    def create_individual_migration(self, source: Entity, target_id: str):
        self.remove_individual_migration(source.id)
        
        migration = Migration(
            source_id=source.id,
            target_id=target_id,
            transactions_count=source.transactions_count
        )
        self.migrations.append(migration)
        
    def remove_individual_migration(self, source_id: str):
        self.migrations = [m for m in self.migrations if m.source_id != source_id]
                
    def get_migrations(self) -> List[Migration]:
        return self.migrations