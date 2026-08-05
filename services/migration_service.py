from typing import List
from models.entity import FornecedorEntity 
from models.migration import Migration

class MigrationService:
    def __init__(self):
        self.migracoes: List[Migration] = []

    def criar_migracao_individual(self, origem: FornecedorEntity, destino_id: str):
       
        self.migracoes = [m for m in self.migracoes if m.origem != origem.id]

      
        migracao = Migration(
            origem=origem.id,
            destino=destino_id,
            quantidade_movimentacoes=origem.movimentacoes
        )
        self.migracoes.append(migracao)
                
    def obter_migracoes(self) -> List[Migration]:
        return self.migracoes