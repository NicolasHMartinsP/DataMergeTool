import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from difflib import SequenceMatcher
from models.duplicate_group import DuplicateGroup

class DuplicateService:
    def __init__(self, mode: int):
        self.mode = mode
        
        if self.mode == 1:
            self.threshold = getattr(config, 'MODE_1_SIMILARITY_THRESHOLD', 85) / 100.0
        else:
            self.threshold = getattr(config, 'MODE_2_SIMILARITY_THRESHOLD', 90) / 100.0

    def calculate_similarity(self, str1: str, str2: str) -> float:
        if not str1 or not str2:
            return 0.0
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
        
    def _clean_text(self, text: str) -> str:
        return str(text).strip().upper()

    def find_duplicates(self, records, transaction_counts):
        """
        Identifies and groups duplicated records based on string similarity.
        Prioritizes records with the highest transaction counts.
        """
        for reg in records:
            if reg.id in transaction_counts:
                reg.transactions_by_store = transaction_counts[reg.id].copy()
                reg.transactions_count = sum(reg.transactions_by_store.values())
            else:
                reg.transactions_count = 0
                reg.transactions_by_store = {}

        groups = []
        processed_ids = set()
        
        # Sort by most transactions first, then alphabetically
        sorted_records = sorted(records, key=lambda x: (x.transactions_count, x.name), reverse=True)
        
        for i, master_record in enumerate(sorted_records):
            if master_record.id in processed_ids:
                continue
                
            duplicate_group = []
            clean_master_name = self._clean_text(master_record.name)
            
            if clean_master_name == "SEM NOME" or not clean_master_name:
                continue
            
            for candidate_record in sorted_records[i+1:]:
                if candidate_record.id in processed_ids:
                    continue
                    
                clean_candidate_name = self._clean_text(candidate_record.name)
                
                if clean_candidate_name == "SEM NOME" or not clean_candidate_name:
                    continue
                
                similarity = self.calculate_similarity(clean_master_name, clean_candidate_name)
                
                if similarity >= self.threshold:
                    duplicate_group.append(candidate_record)
                    processed_ids.add(candidate_record.id)
            
            if duplicate_group:
                processed_ids.add(master_record.id)
                similarity_percentage = int(self.threshold * 100)
                reason = f"Name Similarity >= {similarity_percentage}%"
                
                group = DuplicateGroup(name=master_record.name, master=master_record, duplicates=duplicate_group, reason=reason)
                groups.append(group)
                
        return groups

    def find_by_id(self, search_id: str, records):
        search_id = str(search_id).strip()
        for r in records:
            if str(r.id).strip() == search_id:
                return r
        return None

    def search_by_partial_name(self, term: str, records):
        term = str(term).strip().lower()
        results = []
        for r in records:
            if term in r.name.lower() or term in str(r.id).lower():
                results.append(r)
        return results