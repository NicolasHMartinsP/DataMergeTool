import sys
import os
# Força o Python a enxergar a pasta raiz do projeto (onde está o config.py e o credentials.json)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openpyxl
from collections import defaultdict
import config
from utils import console as utils_console

# Importações da Nuvem
import gspread
from google.oauth2.service_account import Credentials

class Registro:
    def __init__(self, id_reg, nome):
        self.id = str(id_reg).strip()
        self.nome = str(nome).strip()
        self.movimentacoes = 0
        self.movimentacoes_por_loja = {}

class ExcelService:
    def __init__(self):
        # Integração total com o seu config.py
        self.base_sheet_fornecedor = getattr(config, 'ABA_BASE_FORNECEDORES', "Fornecedores")
        self.base_sheet_produto = getattr(config, 'ABA_BASE_PRODUTOS', "Produto")
        
        self.abas_permitidas_fornecedor = getattr(config, 'ABAS_PERMITIDAS_FORNECEDORES', ["Contas a Pagar", "Notas"])
        self.abas_permitidas_produto = getattr(config, 'ABAS_PERMITIDAS_PRODUTOS', ["Itens de Compras", "Notas"])
        
        self.arquivos_para_varrer = []
        self.mapeamento = []
        self.workbooks = {}

    def conectar_nuvem(self):
        """ Autentica o Robô usando o credentials.json para leitura do Google Sheets """
        escopos = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
        
        caminho_credenciais = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "credentials.json")
        
        if not os.path.exists(caminho_credenciais):
            raise Exception("Arquivo 'credentials.json' não encontrado na pasta principal do projeto!")
            
        credenciais = Credentials.from_service_account_file(caminho_credenciais, scopes=escopos)
        cliente = gspread.authorize(credenciais)
        return cliente

    def ler_fornecedores(self):
        """ NOVO BRAÇO NUVEM: Lê a base oficial diretamente do Google Sheets em tempo real """
        try:
            print(f"\n>>> CONECTANDO AOS SERVIDORES DO GOOGLE (NUVEM)...")
            cliente = self.conectar_nuvem()
            
            planilha_nuvem = cliente.open_by_url(config.URL_PLANILHA_MESTRE)
            nome_aba = self.base_sheet_fornecedor if self.modo == 1 else self.base_sheet_produto
            
            try:
                aba = planilha_nuvem.worksheet(nome_aba)
            except gspread.exceptions.WorksheetNotFound:
                aba = planilha_nuvem.sheet1
                
            print(f">>> DOWNLOAD DA BASE OFICIAL ('{nome_aba}') CONCLUÍDO COM SUCESSO!\n")
            
            dados = aba.get_all_values()
            
            if not dados:
                raise Exception("A planilha online está vazia.")
                
            header = [str(h).strip().upper() for h in dados[0]]
            
            col_id = -1
            col_nome = -1
            
            for i, h in enumerate(header):
                palavras = h.replace("_", " ").split()
                if "ID" in palavras or h == "ID":
                    col_id = i
                if h == "NOME":
                    col_nome = i
                    
            if col_id == -1 or col_nome == -1:
                raise Exception("Não foi possível encontrar as colunas 'ID' ou 'NOME' na planilha online.")

            registros = []
            
            for row in dados[1:]:
                if len(row) > col_id and len(row) > col_nome:
                    val_id = row[col_id]
                    val_nome = row[col_nome]
                    
                    if val_id and str(val_id).strip() != "":
                        nome_limpo = val_nome if val_nome else "SEM NOME"
                        registros.append(Registro(val_id, nome_limpo))
                        
            return registros
            
        except Exception as e:
            raise Exception(f"Falha ao ler a planilha oficial na nuvem: {e}")

    def abrir_planilhas(self, modo):
        """ BRAÇO LOCAL: Mantém o scanner de pastas para as Movimentações """
        self.modo = modo
        nome_entidade = "FORNECEDORES" if modo == 1 else "PRODUTOS"
        
        # Puxa dinamicamente as colunas exatas que você colocou no config.py
        if modo == 1:
            colunas_alvo = getattr(config, 'COLUNAS_ALVO_FORNECEDORES', ["FORNECEDOR"])
            abas_permitidas = self.abas_permitidas_fornecedor
        else:
            colunas_alvo = getattr(config, 'COLUNAS_ALVO_PRODUTOS', ["PRODUTO"])
            abas_permitidas = self.abas_permitidas_produto
        
        print(f"\n>>> SCANNER LOCAL ATIVADO: Varrendo APENAS as abas permitidas de {nome_entidade}...\n")
        
        arquivos_na_pasta = []
        for root, dirs, files in os.walk("."):
            if ".venv" in root or "__pycache__" in root or ".git" in root:
                continue
            for f in files:
                if f.endswith(".xlsx") and not f.startswith("~") and "ATUALIZADO" not in f and "LIMPO" not in f and "The Best Almeida" not in f:
                    arquivos_na_pasta.append(os.path.join(root, f))
        
        for arquivo in arquivos_na_pasta:
            try:
                wb = openpyxl.load_workbook(arquivo, data_only=False)
                self.workbooks[arquivo] = wb
                
                for aba_nome in wb.sheetnames:
                    if any(permitida.upper() in aba_nome.upper() for permitida in abas_permitidas):
                        aba = wb[aba_nome]
                        
                        header = []
                        for cell in aba[1]:
                            header.append(str(cell.value).strip().upper() if cell.value else "")
                        
                        for col_idx, col_name in enumerate(header):
                            if any(alvo.upper() in col_name for alvo in colunas_alvo):
                                self.mapeamento.append({
                                    'arquivo': arquivo,
                                    'aba': aba_nome,
                                    'col_idx': col_idx + 1,
                                    'col_nome': col_name
                                })
            except Exception as e:
                print(f"[AVISO] Ignorando arquivo local {arquivo} devido a erro de leitura.")

    def contar_movimentacoes(self):
        """ BRAÇO LOCAL: Conta as ocorrências dentro das planilhas físicas """
        contagem = defaultdict(lambda: defaultdict(int))
        
        for mapa in self.mapeamento:
            wb = self.workbooks[mapa['arquivo']]
            aba = wb[mapa['aba']]
            col_idx = mapa['col_idx']
            
            context_name = f"{mapa['arquivo'].replace('.xlsx','')} | {mapa['aba']} | {mapa.get('col_nome', 'Desconhecida')}"
            
            for row in aba.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
                for cell in row:
                    val = cell.value
                    if val is not None and str(val).strip() != "":
                        val_str = str(val).strip()
                        contagem[val_str][context_name] += 1
                        
        return contagem

    def atualizar_ids(self, migracoes):
        """ BRAÇO LOCAL: Atualiza os IDs antigos apenas nas planilhas locais """
        mapa_migracao = {m.origem: m.destino for m in migracoes}
        
        for mapa in self.mapeamento:
            wb = self.workbooks[mapa['arquivo']]
            aba = wb[mapa['aba']]
            col_idx = mapa['col_idx']
            
            for row in aba.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
                for cell in row:
                    val = cell.value
                    if val is not None and str(val).strip() != "":
                        val_str = str(val).strip()
                        if val_str in mapa_migracao:
                            cell.value = mapa_migracao[val_str]

    def validar_migracoes(self, migracoes):
        """ BRAÇO LOCAL: Valida se as substituições ocorreram corretamente """
        ids_problematicos = [m.origem for m in migracoes]
        falhas = []
        
        for mapa in self.mapeamento:
            wb = self.workbooks[mapa['arquivo']]
            aba = wb[mapa['aba']]
            col_idx = mapa['col_idx']
            
            for row in aba.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
                for cell in row:
                    val = cell.value
                    if val is not None and str(val).strip() != "":
                        val_str = str(val).strip()
                        if val_str in ids_problematicos:
                            falhas.append(f"FALHA: ID '{val_str}' ainda existe em {mapa['arquivo']} -> {mapa['aba']} (Linha {cell.row})")
                            
        return falhas

    def salvar_planilhas(self):
        """ BRAÇO LOCAL: Salva os arquivos físicos atualizados """
        salvos = []
        for arquivo, wb in self.workbooks.items():
            pasta, nome_arquivo = os.path.split(arquivo)
            nome_salvo = os.path.join(pasta, f"ATUALIZADO_{nome_arquivo}")
            wb.save(nome_salvo)
            salvos.append(nome_salvo)
        return salvos

    def salvar_base_fornecedores_limpa(self, ids_remover):
        """ NUVEM: Apenas exibe o aviso, já que o usuário não quer modificar a nuvem """
        aviso = "A limpeza automatica da Base Oficial está desabilitada no modo Leitura em Nuvem. Por favor, apague os IDs descontinuados manualmente no Google Sheets."
        return aviso