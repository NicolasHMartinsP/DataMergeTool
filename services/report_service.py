from typing import List
from models.duplicate_group import DuplicateGroup
from utils import console

class ReportService:
    def show_report(self, groups: List[DuplicateGroup]):
        console.limpar_tela()
        console.titulo("DATA MERGE TOOL v8.0")
        
        if not groups:
            print("Nenhum fornecedor duplicado encontrado.")
            return

        for group in groups:
            print(f"Fornecedor: {group.name}")
            print(f"Agrupado por: [{group.reason}]\n")
            print(f"{'ID':<14} {'Qtd':<6} {'Rastreio por Loja'}\n")
            
            for item in group.duplicates:
                store_details = " | ".join([f"{store}: {qty}" for store, qty in item.transactions_by_store.items()])
                details_str = f"({store_details})" if store_details else ""
                
                print(f"{item.id:<14} {item.transactions_count:<6} {item.name} {details_str}")
                
            print(f"\nSugestão Global:\n{group.master.id}\n")
            console.separador()
            
    def show_validation(self, failures: List[str], saved_files: List[str]):
        console.separador()
        if failures:
            console.erro(f"Validação com ressalvas: {len(failures)} IDs antigos ainda constam nas planilhas:")
            print(failures)
        else:
            console.sucesso("Validação concluída: 100% dos IDs antigos foram substituídos nas planilhas locais.")
            console.sucesso(f"{len(saved_files)} planilhas de movimentações salvas e atualizadas:\n")
            for file in saved_files:
                print(f" -> {file}")