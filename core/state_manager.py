import json
import os

class StateManager:
    def __init__(self, backup_file: str):
        self.backup_file = backup_file
        self.current_session = {}
        self.action_history = []
        self.processed_ids = set()

    def save_state(self):
        """Persists the current state and action history to a JSON backup file."""
        serialized_history = []
        for action in self.action_history:
            serialized_history.append({
                'type': action['type'],
                'group_idx': action['group_idx'],
                'target_ids': [a['obj'].id for a in action['targets']],
                'dest_entity_id': action['dest_entity'].id if action.get('dest_entity') else None
            })
        
        data = {
            "current_session": self.current_session,
            "history": serialized_history
        }
        
        with open(self.backup_file, "w", encoding="utf-8") as out:
            json.dump(data, out, ensure_ascii=False, indent=4)

    def load_backup(self, entities, duplicate_service, migration_service):
        """Attempts to restore session state from a previous JSON backup."""
        if not os.path.exists(self.backup_file):
            return

        try:
            with open(self.backup_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            session_raw = data.get("current_session", {})
            history_raw = data.get("history", [])

            if history_raw:
                for action_raw in history_raw:
                    action_type = action_raw.get('type', 'M')
                    group_idx = action_raw.get('group_idx', 'RECOVERED')
                    dest_id = action_raw.get('dest_entity_id')
                    dest_entity = duplicate_service.find_by_id(dest_id, entities) if dest_id else None
                    
                    target_objs = [duplicate_service.find_by_id(tid, entities) for tid in action_raw.get('target_ids', [])]
                    target_objs = [obj for obj in target_objs if obj]
                    
                    if not target_objs:
                        continue
                    
                    if action_type in ['S', 'I', 'M']: 
                        self.apply_batch_migration(target_objs, dest_id, dest_entity, migration_service, action_type, group_idx, is_restoring=True)
                    elif action_type == 'P': 
                        self.apply_batch_skip(target_objs, group_idx, is_restoring=True)
                        
            elif session_raw:
                for orig, dest in session_raw.items():
                    e_orig = duplicate_service.find_by_id(orig, entities)
                    e_dest = duplicate_service.find_by_id(dest, entities)
                    if e_orig: 
                        self.apply_batch_migration([e_orig], dest, e_dest, migration_service, 'M', 'RECOVERED', is_restoring=True)

        except Exception as e:
            print(f"Failed to load previous backup: {e}")

    def apply_batch_migration(self, targets, dest_id, dest_entity, migration_service, action_type, group_idx, is_restoring=False):
        """Executes a substitution for a batch of entities and tracks the action."""
        targets_data = []
        for entity in targets:
            if entity.id == dest_id:
                continue
            
            targets_data.append({
                'obj': entity,
                'movs': entity.transactions_count,
                'stores': entity.transactions_by_store.copy()
            })
            
            migration_service.create_individual_migration(entity, dest_id)
            self.current_session[entity.id] = dest_id
            self.processed_ids.add(entity.id)
            
            if dest_entity:
                dest_entity.transactions_count += entity.transactions_count
                for store, qty in entity.transactions_by_store.items():
                    dest_entity.transactions_by_store[store] = dest_entity.transactions_by_store.get(store, 0) + qty
                    
            entity.transactions_count = 0
            entity.transactions_by_store = {}

        if targets_data:
            self.action_history.append({
                'type': action_type,
                'group_idx': group_idx,
                'targets': targets_data,
                'dest_entity': dest_entity
            })
            
        if not is_restoring:
            self.save_state()

    def apply_batch_skip(self, targets, group_idx, is_restoring=False):
        """Marks entities as skipped and saves to history."""
        targets_data = []
        for entity in targets:
            targets_data.append({'obj': entity})
            self.processed_ids.add(entity.id)
            
        if targets_data:
            self.action_history.append({
                'type': 'P',
                'group_idx': group_idx,
                'targets': targets_data,
                'dest_entity': None
            })
        
        if not is_restoring:
            self.save_state()

    def undo_last_action(self, action_payload, migration_service):
        """Reverts a previously tracked action, restoring counts and states."""
        dest_entity = action_payload['dest_entity']
        action_type = action_payload['type']
        
        if action_type in ['S', 'I', 'M']:
            for target_data in action_payload['targets']:
                entity = target_data['obj']
                t_movs = target_data['movs']
                t_stores = target_data['stores']
                
                migration_service.remove_individual_migration(entity.id)
                
                if entity.id in self.current_session:
                    del self.current_session[entity.id]
                self.processed_ids.discard(entity.id)
                
                if dest_entity and entity.id != dest_entity.id: 
                    dest_entity.transactions_count -= t_movs
                    for store, qty in t_stores.items():
                        dest_entity.transactions_by_store[store] -= qty
                        if dest_entity.transactions_by_store[store] <= 0:
                            del dest_entity.transactions_by_store[store]
                            
                entity.transactions_count = t_movs
                entity.transactions_by_store = t_stores.copy()
                
        elif action_type == 'P':
            for target_data in action_payload['targets']: 
                self.processed_ids.discard(target_data['obj'].id)
        
        self.save_state()

    def update_group_pending_items(self, duplicate_groups):
        """Updates the visual lists of pending items in duplicate groups."""
        for group in duplicate_groups:
            group.pending_items = [item for item in group.duplicates if item.id not in self.processed_ids]