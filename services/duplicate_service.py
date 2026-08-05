import unicodedata
import re
from difflib import SequenceMatcher
from typing import List, Dict, Optional
from models.entity import FornecedorEntity
from models.duplicate_group import DuplicateGroup

class DuplicateService:
    def _sanitizar_nome(self, nome: str) -> str:
        """ Remove acentos, pontuações e sufixos empresariais para melhorar o match """
        # Remove acentos
        nome_limpo = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('utf-8')
        nome_limpo = nome_limpo.upper()
        
        # Troca caracteres especiais por espaço
        nome_limpo = re.sub(r'[^A-Z0-9\s]', ' ', nome_limpo)
        
        # Remove sufixos inúteis no final do nome
        sufixos = [' LTDA', ' SA', ' S A', ' ME', ' EPP']
        for sufixo in sufixos:
            if nome_limpo.endswith(sufixo):
                nome_limpo = nome_limpo[:-len(sufixo)]
                
        # Remove espaços duplos
        return re.sub(r'\s+', ' ', nome_limpo).strip()

    def encontrar_duplicados(self, fornecedores: List[FornecedorEntity], contagem: Dict[str, Dict]) -> List[DuplicateGroup]:
        # 1. Atualizar movimentações
        for f in fornecedores:
            dados_contagem = contagem.get(f.id, {'total': 0, 'lojas': {}})
            f.movimentacoes = dados_contagem['total']
            f.movimentacoes_por_loja = dados_contagem['lojas']
            f.nome_comparacao = self._sanitizar_nome(f.nome)
        
        # 2. Agrupamento Inteligente (Exato + Levenshtein via difflib)
        grupos_temporarios = [] # Lista de dicts: {'nome_base': str, 'itens': [], 'motivo': str}
        
        for f in fornecedores:
            adicionado = False
            
            for g in grupos_temporarios:
                # Match Exato (após sanitizar)
                if f.nome_comparacao == g['nome_base']:
                    g['itens'].append(f)
                    adicionado = True
                    break
                
                # Match por Similaridade (>= 85%)
                similaridade = SequenceMatcher(None, f.nome_comparacao, g['nome_base']).ratio()
                if similaridade >= 0.85:
                    g['itens'].append(f)
                    g['motivo'] = f"Similaridade (~{int(similaridade * 100)}%)"
                    adicionado = True
                    break
                    
            if not adicionado:
                grupos_temporarios.append({
                    'nome_base': f.nome_comparacao,
                    'nome_exibicao': f.nome, # Guarda o nome real e bonito para a interface
                    'itens': [f],
                    'motivo': 'Exato'
                })
        
        # 3. Filtrar apenas os duplicados e converter para a Model
        grupos_duplicados = []
        for g in grupos_temporarios:
            if len(g['itens']) > 1:
                lista_ordenada = sorted(g['itens'], key=lambda x: x.movimentacoes, reverse=True)
                mestre = lista_ordenada[0]
                
                grupos_duplicados.append(DuplicateGroup(
                    nome=g['nome_exibicao'],
                    mestre=mestre,
                    duplicados=lista_ordenada,
                    motivo=g['motivo']
                ))
                
        return grupos_duplicados

    def buscar_por_id(self, id_busca: str, fornecedores: List[FornecedorEntity]) -> Optional[FornecedorEntity]:
        for f in fornecedores:
            if f.id == id_busca:
                return f
        return None