import os
import pandas as pd
from typing import List, Dict
import config
from models.entity import FornecedorEntity
from models.migration import Migration
from utils import console

class ExcelService:
    def __init__(self):
        self.df_fornecedores = None
        self.lojas_data: Dict[str, Dict[str, pd.DataFrame]] = {}

    def _garantir_pastas(self):
        os.makedirs(config.PASTA_MOVIMENTACOES, exist_ok=True)
        os.makedirs(config.PASTA_SAIDA, exist_ok=True)

    def abrir_planilhas(self):
        self._garantir_pastas()
        
        try:
            self.df_fornecedores = pd.read_excel(config.ARQUIVO_FORNECEDORES, sheet_name=config.ABA_FORNECEDOR)
        except FileNotFoundError:
            raise Exception(f"Arquivo {config.ARQUIVO_FORNECEDORES} não encontrado na raiz do projeto.")

        arquivos_na_pasta = os.listdir(config.PASTA_MOVIMENTACOES)
        planilhas_validas = [f for f in arquivos_na_pasta if f.endswith('.xlsx') and not f.startswith('~$')]
        
        if not planilhas_validas:
            raise Exception(f"Nenhuma planilha válida encontrada na pasta '{config.PASTA_MOVIMENTACOES}'.")

        for arquivo in planilhas_validas:
            caminho_completo = os.path.join(config.PASTA_MOVIMENTACOES, arquivo)
            try:
                df_notas = pd.read_excel(caminho_completo, sheet_name=config.ABA_NOTAS)
                df_compras = pd.read_excel(caminho_completo, sheet_name=config.ABA_NOTAS_COMPRA)
                
                self.lojas_data[arquivo] = {
                    config.ABA_NOTAS: df_notas,
                    config.ABA_NOTAS_COMPRA: df_compras
                }
            except Exception as e:
                console.erro(f"Falha ao ler abas do arquivo {arquivo}: {str(e)}")
                raise

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

    def contar_movimentacoes(self) -> Dict[str, Dict]:
        contagem = {}
        
        # Varre loja por loja
        for arquivo, abas in self.lojas_data.items():
            ids_notas = abas[config.ABA_NOTAS][config.COLUNA_FORNECEDOR].dropna().apply(self._limpar_id).tolist()
            ids_compras = abas[config.ABA_NOTAS_COMPRA][config.COLUNA_FORNECEDOR].dropna().apply(self._limpar_id).tolist()
            todos_ids_nesta_loja = ids_notas + ids_compras
            
            for f_id in todos_ids_nesta_loja:
                if f_id not in contagem:
                    contagem[f_id] = {'total': 0, 'lojas': {}}
                
                # Incrementa o total global e o total da loja específica
                contagem[f_id]['total'] += 1
                contagem[f_id]['lojas'][arquivo] = contagem[f_id]['lojas'].get(arquivo, 0) + 1
                
        return contagem

    def atualizar_ids(self, migracoes: List[Migration]):
        if not migracoes:
            return
        mapa_migracao = {m.origem: m.destino for m in migracoes}
        def substituir(val):
            if pd.isna(val):
                return val
            id_str = self._limpar_id(val)
            return mapa_migracao.get(id_str, id_str)

        for arquivo, abas in self.lojas_data.items():
            abas[config.ABA_NOTAS][config.COLUNA_FORNECEDOR] = abas[config.ABA_NOTAS][config.COLUNA_FORNECEDOR].apply(substituir)
            abas[config.ABA_NOTAS_COMPRA][config.COLUNA_FORNECEDOR] = abas[config.ABA_NOTAS_COMPRA][config.COLUNA_FORNECEDOR].apply(substituir)

    def validar_migracoes(self, migracoes: List[Migration]) -> List[str]:
        todos_ids_atuais = []
        for abas in self.lojas_data.values():
            ids_notas = abas[config.ABA_NOTAS][config.COLUNA_FORNECEDOR].dropna().apply(self._limpar_id).tolist()
            ids_compras = abas[config.ABA_NOTAS_COMPRA][config.COLUNA_FORNECEDOR].dropna().apply(self._limpar_id).tolist()
            todos_ids_atuais.extend(ids_notas + ids_compras)
            
        todos_ids_set = set(todos_ids_atuais)
        falhas = [m.origem for m in migracoes if m.origem in todos_ids_set]
        return falhas

    def salvar_planilhas(self) -> List[str]:
        arquivos_salvos = []
        for arquivo, abas in self.lojas_data.items():
            caminho_saida = os.path.join(config.PASTA_SAIDA, f"MERGED_{arquivo}")
            with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
                abas[config.ABA_NOTAS].to_excel(writer, sheet_name=config.ABA_NOTAS, index=False)
                abas[config.ABA_NOTAS_COMPRA].to_excel(writer, sheet_name=config.ABA_NOTAS_COMPRA, index=False)
            arquivos_salvos.append(caminho_saida)
        return arquivos_salvos

    def salvar_base_fornecedores_limpa(self, ids_removidos: List[str]) -> str:
        """ Remove as linhas dos fornecedores que foram migrados e salva a base limpa """
        ids_removidos_set = set(ids_removidos)
        
        # Mantém apenas a linha cujo ID limpo NÃO esteja na lista de removidos
        mascara = self.df_fornecedores[config.COLUNA_ID].apply(
            lambda x: pd.notna(x) and self._limpar_id(x) not in ids_removidos_set
        )
        
        df_limpo = self.df_fornecedores[mascara]
        
        caminho_saida = os.path.join(config.PASTA_SAIDA, f"ATUALIZADO_{config.ARQUIVO_FORNECEDORES}")
        df_limpo.to_excel(caminho_saida, sheet_name=config.ABA_FORNECEDOR, index=False)
        return caminho_saida