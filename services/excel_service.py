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
        # Agora o sistema possui 2 motores paralelos na memória
        self.dados_movimentacoes: Dict[str, Dict[str, pd.DataFrame]] = {}
        self.dados_contas: Dict[str, Dict[str, pd.DataFrame]] = {}

    def _garantir_pastas(self):
        os.makedirs(config.PASTA_MOVIMENTACOES, exist_ok=True)
        os.makedirs(config.PASTA_CONTAS, exist_ok=True)
        os.makedirs(config.PASTA_SAIDA, exist_ok=True)

    def abrir_planilhas(self):
        self._garantir_pastas()
        
        # 1. Carrega The Best Almeida
        try:
            self.df_fornecedores = pd.read_excel(config.ARQUIVO_FORNECEDORES, sheet_name=config.ABA_FORNECEDOR)
        except FileNotFoundError:
            raise Exception(f"Arquivo {config.ARQUIVO_FORNECEDORES} não encontrado na raiz do projeto.")

        # 2. Carrega as Movimentações (Todas as abas para não perder o histórico)
        arquivos_mov = [f for f in os.listdir(config.PASTA_MOVIMENTACOES) if f.endswith('.xlsx') and not f.startswith('~$')]
        for arquivo in arquivos_mov:
            caminho = os.path.join(config.PASTA_MOVIMENTACOES, arquivo)
            self.dados_movimentacoes[arquivo] = {}
            xls = pd.ExcelFile(caminho)
            for aba in xls.sheet_names:
                self.dados_movimentacoes[arquivo][aba] = pd.read_excel(xls, sheet_name=aba)

        # 3. Carrega as Contas (Todas as abas)
        arquivos_contas = [f for f in os.listdir(config.PASTA_CONTAS) if f.endswith('.xlsx') and not f.startswith('~$')]
        for arquivo in arquivos_contas:
            caminho = os.path.join(config.PASTA_CONTAS, arquivo)
            self.dados_contas[arquivo] = {}
            xls = pd.ExcelFile(caminho)
            for aba in xls.sheet_names:
                self.dados_contas[arquivo][aba] = pd.read_excel(xls, sheet_name=aba)

        if not self.dados_movimentacoes and not self.dados_contas:
            console.aviso("AVISO: Nenhuma planilha encontrada nas pastas 'movimentacoes' ou 'contas'.")

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
        
        def adicionar_contagem(df, col_name, nome_arquivo):
            if col_name in df.columns:
                ids = df[col_name].dropna().apply(self._limpar_id).tolist()
                for f_id in ids:
                    if f_id not in contagem:
                        contagem[f_id] = {'total': 0, 'lojas': {}}
                    contagem[f_id]['total'] += 1
                    contagem[f_id]['lojas'][nome_arquivo] = contagem[f_id]['lojas'].get(nome_arquivo, 0) + 1

        # Conta o total de notas cruzando Movimentações e Contas ao mesmo tempo
        for arquivo, abas in self.dados_movimentacoes.items():
            for aba_nome in config.ABAS_MOVIMENTACOES_FORNECEDOR:
                if aba_nome in abas:
                    adicionar_contagem(abas[aba_nome], config.COLUNA_FORNECEDOR, arquivo)

        for arquivo, abas in self.dados_contas.items():
            for aba_nome in config.ABAS_CONTAS_FORNECEDOR:
                if aba_nome in abas:
                    adicionar_contagem(abas[aba_nome], config.COLUNA_FORNECEDOR, arquivo)

        return contagem

    def atualizar_ids(self, migracoes: List[Migration]):
        if not migracoes:
            return
            
        mapa_migracao = {str(m.origem): str(m.destino) for m in migracoes}
        
        def substituir(val):
            if pd.isna(val): return val
            id_str = self._limpar_id(val)
            return mapa_migracao.get(id_str, id_str)

        # Faz o Update (Localizar/Substituir) em Movimentações
        for arquivo, abas in self.dados_movimentacoes.items():
            for aba_nome in config.ABAS_MOVIMENTACOES_FORNECEDOR:
                if aba_nome in abas and config.COLUNA_FORNECEDOR in abas[aba_nome].columns:
                    abas[aba_nome][config.COLUNA_FORNECEDOR] = abas[aba_nome][config.COLUNA_FORNECEDOR].apply(substituir)

        # Faz o Update em Contas (O salvador do AppSheet)
        for arquivo, abas in self.dados_contas.items():
            for aba_nome in config.ABAS_CONTAS_FORNECEDOR:
                if aba_nome in abas and config.COLUNA_FORNECEDOR in abas[aba_nome].columns:
                    abas[aba_nome][config.COLUNA_FORNECEDOR] = abas[aba_nome][config.COLUNA_FORNECEDOR].apply(substituir)

    def validar_migracoes(self, migracoes: List[Migration]) -> List[str]:
        todos_ids_atuais = set()
        
        for abas in self.dados_movimentacoes.values():
            for aba_nome in config.ABAS_MOVIMENTACOES_FORNECEDOR:
                if aba_nome in abas and config.COLUNA_FORNECEDOR in abas[aba_nome].columns:
                    ids = abas[aba_nome][config.COLUNA_FORNECEDOR].dropna().apply(self._limpar_id).tolist()
                    todos_ids_atuais.update(ids)
                    
        for abas in self.dados_contas.values():
            for aba_nome in config.ABAS_CONTAS_FORNECEDOR:
                if aba_nome in abas and config.COLUNA_FORNECEDOR in abas[aba_nome].columns:
                    ids = abas[aba_nome][config.COLUNA_FORNECEDOR].dropna().apply(self._limpar_id).tolist()
                    todos_ids_atuais.update(ids)

        falhas = [m.origem for m in migracoes if m.origem in todos_ids_atuais]
        return falhas

    def salvar_planilhas(self) -> List[str]:
        arquivos_salvos = []
        
        # Salva os 8 arquivos MERGED das Movimentações (com todas as abas originais)
        for arquivo, abas in self.dados_movimentacoes.items():
            caminho_saida = os.path.join(config.PASTA_SAIDA, f"MERGED_{arquivo}")
            with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
                for aba_nome, df in abas.items():
                    df.to_excel(writer, sheet_name=aba_nome, index=False)
            arquivos_salvos.append(caminho_saida)

        # Salva os 8 arquivos MERGED das Contas a Pagar
        for arquivo, abas in self.dados_contas.items():
            caminho_saida = os.path.join(config.PASTA_SAIDA, f"MERGED_{arquivo}")
            with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
                for aba_nome, df in abas.items():
                    df.to_excel(writer, sheet_name=aba_nome, index=False)
            arquivos_salvos.append(caminho_saida)
            
        return arquivos_salvos

    def salvar_base_fornecedores_limpa(self, ids_mortos: list):
        if not ids_mortos:
            return None
            
        df_base = self.df_fornecedores.copy() 
        col = config.COLUNA_ID
        
        df_base[col] = df_base[col].astype(str).str.strip()
        ids_mortos_limpos = [str(i).strip() for i in ids_mortos]
        
        df_limpo = df_base[~df_base[col].isin(ids_mortos_limpos)]
        
        nome_arquivo = "ATUALIZADO_The Best Almeida.xlsx"
        df_limpo.to_excel(nome_arquivo, index=False)
        return nome_arquivo