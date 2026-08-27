import config
from collections import defaultdict

class CrossService:
    def __init__(self):
        self.resolved_count = 0

    def scan_referential_integrity(self, workbooks, master_records):
        """Scans physical files and cross-references Side A (e.g. Bills) with Side B (e.g. Invoices) ensuring integrity."""
        master_ids = {str(f.id).strip().lower(): f for f in master_records}
        transactions_map = defaultdict(lambda: {'bills': [], 'invoices': []})
        
        bills_keywords = getattr(config, 'CROSS_BILLS_SHEET_KEYWORDS', [])
        invoices_keywords = getattr(config, 'CROSS_INVOICES_SHEET_KEYWORDS', [])
        
        for file_path, wb in workbooks.items():
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                sheet_upper = sheet_name.upper().strip()
                
                sheet_type = None
                link_col_name = ""
                entity_col_name = ""
                
                if any(kw.upper() in sheet_upper for kw in bills_keywords):
                    sheet_type = 'BILLS'
                    link_col_name = getattr(config, 'CROSS_BILLS_LINK_COLUMN', "NOTA").upper()
                    entity_col_name = getattr(config, 'CROSS_BILLS_ENTITY_COLUMN', "FORNECEDOR").upper()
                elif any(kw.upper() in sheet_upper for kw in invoices_keywords):
                    sheet_type = 'INVOICES'
                    link_col_name = getattr(config, 'CROSS_INVOICES_LINK_COLUMN', "ID").upper()
                    entity_col_name = getattr(config, 'CROSS_INVOICES_ENTITY_COLUMN', "FORNECEDOR").upper()
                else:
                    continue
                    
                header = [str(c.value).strip().upper() if c.value else "" for c in sheet[1]]
                
                link_col_idx = -1
                entity_col_idx = -1
                
                for i, h in enumerate(header):
                    if h == link_col_name:
                        link_col_idx = i + 1
                    if h == entity_col_name:
                        entity_col_idx = i + 1
                        
                if link_col_idx == -1 or entity_col_idx == -1:
                    continue
                    
                for row in sheet.iter_rows(min_row=2):
                    link_cell = row[link_col_idx - 1]
                    entity_cell = row[entity_col_idx - 1]
                    
                    val_link = str(link_cell.value).strip() if link_cell.value is not None else ""
                    if val_link.endswith(".0"): 
                        val_link = val_link[:-2]
                    if not val_link or val_link.lower() == "none": 
                        continue
                    
                    val_entity = str(entity_cell.value).strip() if entity_cell.value is not None else ""
                    if val_entity.endswith(".0"): 
                        val_entity = val_entity[:-2]
                    if val_entity.lower() == "none": 
                        val_entity = ""
                    
                    data_entry = {
                        'file': file_path,
                        'sheet': sheet_name,
                        'row': entity_cell.row,
                        'val': val_entity,
                        'cell': entity_cell
                    }
                    
                    if sheet_type == 'BILLS':
                        transactions_map[val_link]['bills'].append(data_entry)
                    else:
                        transactions_map[val_link]['invoices'].append(data_entry)
                        
        conflicts = []
        for transaction_id, details in transactions_map.items():
            if not details['bills'] or not details['invoices']: 
                continue 
            
            filled_bills = [c for c in details['bills'] if c['val'] != ""]
            primary_bill = filled_bills[0] if filled_bills else details['bills'][0]
            
            filled_invoices = [n for n in details['invoices'] if n['val'] != ""]
            primary_invoice = filled_invoices[0] if filled_invoices else details['invoices'][0]
            
            id_bill = primary_bill['val'].lower()
            id_invoice = primary_invoice['val'].lower()
            
            if id_bill == "" and id_invoice == "":
                continue
            
            if id_bill == id_invoice and id_bill in master_ids: 
                continue
            
            def get_status(val):
                if not val: return "EMPTY"
                if val in master_ids: return "OFFICIAL"
                return "ORPHAN"
                
            status_bill = get_status(id_bill)
            status_invoice = get_status(id_invoice)
            
            suggestion_id = None
            suggestion_name = ""
            if status_bill == "OFFICIAL" and status_invoice != "OFFICIAL": 
                suggestion_id = primary_bill['val']
                suggestion_name = master_ids[id_bill].name
            elif status_invoice == "OFFICIAL" and status_bill != "OFFICIAL":
                suggestion_id = primary_invoice['val']
                suggestion_name = master_ids[id_invoice].name
                
            conflicts.append({
                'transaction_id': transaction_id,
                'bill': primary_bill,
                'invoice': primary_invoice,
                'status_bill': status_bill,
                'status_invoice': status_invoice,
                'suggestion_id': suggestion_id,
                'suggestion_name': suggestion_name
            })
            
        return conflicts

    def apply_resolution(self, conflict, new_id: str):
        """Updates the physical memory cell with the new resolved ID."""
        conflict['bill']['cell'].value = new_id
        conflict['invoice']['cell'].value = new_id
        self.resolved_count += 1