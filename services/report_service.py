from typing import List
from models.duplicate_group import DuplicateGroup
from utils import console

class ReportService:
    def mostrar_relatorio(self, grupos: List[DuplicateGroup]):
        console.limpar_tela()
        console.titulo("DATA MERGE TOOL")
        
        if not grupos:
            print("Nenhum fornecedor duplicado encontrado.")
            return

        for grupo in grupos:
            print(f"Fornecedor: {grupo.nome}\n")
            print(f"{'ID':<13} {'Movimentações'}\n")
            
            for f in grupo.duplicados:
                print(f"{f.id:<14} {f.movimentacoes}")
                
            print(f"\nSugestão:\n{grupo.mestre.id}\n")
            console.separador()