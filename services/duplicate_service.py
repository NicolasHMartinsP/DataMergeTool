from typing import List, Dict
from models.entity import FornecedorEntity
from models.duplicate_group import DuplicateGroup

class DuplicateService:
    def encontrar_duplicados(self, fornecedores: List[FornecedorEntity], contagem: Dict[int, int]) -> List[DuplicateGroup]:
   
        for f in fornecedores:
            f.movimentacoes = contagem.get(f.id, 0)
        
        grupos_por_nome = {}
        for f in fornecedores:
            if f.nome not in grupos_por_nome:
                grupos_por_nome[f.nome] = []
            grupos_por_nome[f.nome].append(f)
        
        grupos_duplicados = []
        for nome, lista in grupos_por_nome.items():
            if len(lista) > 1:
            
                lista_ordenada = sorted(lista, key=lambda x: x.movimentacoes, reverse=True)
                mestre = lista_ordenada[0]
                
                grupos_duplicados.append(DuplicateGroup(
                    nome=nome,
                    mestre=mestre,
                    duplicados=lista_ordenada
                ))
                
        return grupos_duplicados