from typing import List
from models.duplicate_group import DuplicateGroup
from models.migration import Migration

class MigrationService:
    def __init__(self):
        self.migracoes: List[Migration] = []

    def criar_migracoes(self, grupo: DuplicateGroup, id_mestre_escolhido: str):
        # Sem travas. O ID mestre pode pertencer a outra base/planilha.
        for f in grupo.duplicados:
            if f.id != id_mestre_escolhido:
                migracao = Migration(
                    origem=f.id,
                    destino=id_mestre_escolhido,
                    quantidade_movimentacoes=f.movimentacoes
                )
                self.migracoes.append(migracao)
                
    def obter_migracoes(self) -> List[Migration]:
        return self.migracoes