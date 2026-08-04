from typing import List, Dict, Optional
from models.entity import FornecedorEntity
from models.duplicate_group import DuplicateGroup

class DuplicateService:
    def encontrar_duplicados(self, fornecedores: List[FornecedorEntity], contagem: Dict[str, Dict]) -> List[DuplicateGroup]:
        for f in fornecedores:
            # Extrai os dados do dicionário complexo que veio do ExcelService
            dados_contagem = contagem.get(f.id, {'total': 0, 'lojas': {}})
            
            f.movimentacoes = dados_contagem['total']
            f.movimentacoes_por_loja = dados_contagem['lojas']
        
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

    def buscar_por_id(self, id_busca: str, fornecedores: List[FornecedorEntity]) -> Optional[FornecedorEntity]:
        for f in fornecedores:
            if f.id == id_busca:
                return f
        return None