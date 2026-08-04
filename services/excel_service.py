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

    def ler_fornecedores(self) -> List[FornecedorEntity]:
        fornecedores = []
    
        df_limpo = self.df_fornecedores.dropna(subset=[config.COLUNA_ID])
        
        for _, row in df_limpo.iterrows():
            fornecedores.append(FornecedorEntity(
                id=int(row[config.COLUNA_ID]),
                nome=str(row[config.COLUNA_NOME]).strip().upper()
            ))
        return fornecedores

    def contar_movimentacoes(self) -> Dict[int, int]:
        ids_notas = self.df_notas[config.COLUNA_FORNECEDOR].dropna().astype(int).tolist()
        ids_compras = self.df_notas_compra[config.COLUNA_FORNECEDOR].dropna().astype(int).tolist()
        
        todos_ids = ids_notas + ids_compras
        
        contagem = {}
        for f_id in todos_ids:
            contagem[f_id] = contagem.get(f_id, 0) + 1
            
        return contagem