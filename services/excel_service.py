import pandas as pd
from typing import List, Dict
import config
from models.entity import FornecedorEntity

class ExcelService:
    def __init__(self):
        self.df_fornecedores = None
        self.df_notas = None
        self.df_notas_compra = None

    def abrir_planilhas(self):
        self.df_fornecedores = pd.read_excel(config.ARQUIVO_FORNECEDORES, sheet_name=config.ABA_FORNECEDOR)
        self.df_notas = pd.read_excel(config.ARQUIVO_MOVIMENTACOES, sheet_name=config.ABA_NOTAS)
        self.df_notas_compra = pd.read_excel(config.ARQUIVO_MOVIMENTACOES, sheet_name=config.ABA_NOTAS_COMPRA)

    def _limpar_id(self, valor) -> str:
       
        id_str = str(valor).strip()
        if id_str.endswith('.0'):
            return id_str[:-2]
        return id_str

    def ler_fornecedores(self) -> List[FornecedorEntity]:
        fornecedores = []
        df_limpo = self.df_fornecedores.dropna(subset=[config.COLUNA_ID])
        
        for _, row in df_limpo.iterrows():
            fornecedores.append(FornecedorEntity(
                id=self._limpar_id(row[config.COLUNA_ID]),
                nome=str(row[config.COLUNA_NOME]).strip().upper()
            ))
        return fornecedores

    def contar_movimentacoes(self) -> Dict[str, int]:
       
        ids_notas = self.df_notas[config.COLUNA_FORNECEDOR].dropna().apply(self._limpar_id).tolist()
        ids_compras = self.df_notas_compra[config.COLUNA_FORNECEDOR].dropna().apply(self._limpar_id).tolist()
        
        todos_ids = ids_notas + ids_compras
        
        contagem = {}
        for f_id in todos_ids:
            contagem[f_id] = contagem.get(f_id, 0) + 1
            
        return contagem
    # - SPRINT 3
    def atualizar_ids(self, migracoes: List[Migration]):
        if not migracoes:
            return
            
        # Cria mapa De -> Para em O(1) para substituição rápida
        mapa_migracao = {m.origem: m.destino for m in migracoes}
        
        def substituir(val):
            if pd.isna(val):
                return val
            id_str = self._limpar_id(val)
            return mapa_migracao.get(id_str, id_str)

        # Atualiza ambas as abas de movimentações
        self.df_notas[config.COLUNA_FORNECEDOR] = self.df_notas[config.COLUNA_FORNECEDOR].apply(substituir)
        self.df_notas_compra[config.COLUNA_FORNECEDOR] = self.df_notas_compra[config.COLUNA_FORNECEDOR].apply(substituir)

    def validar_migracoes(self, migracoes: List[Migration]) -> List[str]:
        # Verifica se algum ID antigo sobreviveu após a atualização
        ids_notas = self.df_notas[config.COLUNA_FORNECEDOR].dropna().apply(self._limpar_id).tolist()
        ids_compras = self.df_notas_compra[config.COLUNA_FORNECEDOR].dropna().apply(self._limpar_id).tolist()
        
        todos_ids_atuais = set(ids_notas + ids_compras)
        falhas = [m.origem for m in migracoes if m.origem in todos_ids_atuais]
        
        return falhas

    def salvar_planilhas(self) -> str:
        arquivo_saida = f"MERGED_{config.ARQUIVO_MOVIMENTACOES}"
        
        with pd.ExcelWriter(arquivo_saida, engine='openpyxl') as writer:
            self.df_notas.to_excel(writer, sheet_name=config.ABA_NOTAS, index=False)
            self.df_notas_compra.to_excel(writer, sheet_name=config.ABA_NOTAS_COMPRA, index=False)
            
        return arquivo_saida