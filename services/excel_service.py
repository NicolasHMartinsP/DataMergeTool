import sys
import os
# Força o Python a enxergar a pasta raiz do projeto (onde está o config.py)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openpyxl
from collections import defaultdict
import config
from utils import console as utils_console

class Registro:
    """ Objeto genérico que se adapta para Fornecedores, Produtos, etc. """
    def __init__(self, id_reg, nome):
        self.id = str(id_reg).strip()
        self.nome = str(nome).strip() if nome else "SEM NOME"
        self.movimentacoes = 0
        self.movimentacoes_por_loja = defaultdict(int)

class ExcelService:
    def __init__(self):
        self.modo = None
        self.base_file = ""
        self.base_sheet = ""
        self.workbooks = {}
        self.mapeamento = []
        
    def abrir_planilhas(self, modo):
        self.modo = modo
        self.workbooks.clear()
        self.mapeamento.clear()
        
        # Carrega as configurações de acordo com o modo de operação
        if self.modo == 1:
            self.base_file = config.ARQUIVO_BASE_FORNECEDORES
            self.base_sheet = config.ABA_BASE_FORNECEDORES
            colunas_alvo = config.COLUNAS_ALVO_FORNECEDORES
            abas_permitidas = config.ABAS_PERMITIDAS_FORNECEDORES
            nome_entidade = "FORNECEDORES"
        else:
            self.base_file = config.ARQUIVO_BASE_PRODUTOS
            self.base_sheet = config.ABA_BASE_PRODUTOS
            colunas_alvo = config.COLUNAS_ALVO_PRODUTOS
            abas_permitidas = config.ABAS_PERMITIDAS_PRODUTOS
            nome_entidade = "PRODUTOS"

        utils_console.aviso(f"Modo Restrito (Whitelist): Varrendo APENAS as abas permitidas de {nome_entidade}...")

        # Varredura profunda: entra em subpastas (como 'movimentacoes') para achar os arquivos
        arquivos_na_pasta = []
        for root, dirs, files in os.walk("."):
            # Ignora pastas de sistema como .venv ou __pycache__
            if ".venv" in root or "__pycache__" in root or ".git" in root:
                continue
            for f in files:
                if f.endswith(".xlsx") and not f.startswith("~") and "ATUALIZADO" not in f and "LIMPO" not in f:
                    # Salva o caminho completo do arquivo (ex: movimentacoes/Movimentações - Mafra.xlsx)
                    arquivos_na_pasta.append(os.path.join(root, f))
        
        for arquivo in arquivos_na_pasta:
            if arquivo == self.base_file:
                continue # O arquivo da Tabela Pai é lido separadamente
                
            try:
                wb = openpyxl.load_workbook(arquivo)
                self.workbooks[arquivo] = wb
                
                for aba_nome in wb.sheetnames:
                    # TRAVA DE SEGURANÇA MÁXIMA: Ignora qualquer aba fora da Lista Branca
                    if aba_nome not in abas_permitidas:
                        continue 

                    aba = wb[aba_nome]
                    if aba.max_row > 0:
                        header = [str(cell.value).strip().upper() if cell.value else "" for cell in aba[1]]
                        
                        # Match: O Scanner acha a coluna alvo ("Produto 1", "Produto 2") ignorando as de "ID"
                        for col_idx, col_name in enumerate(header):
                         if any(alvo.upper() in col_name for alvo in colunas_alvo):
                                self.mapeamento.append({
                                    'arquivo': arquivo,
                                    'aba': aba_nome,
                                    'col_idx': col_idx + 1,
                                    'col_nome': col_name  # <--- NOVA LINHA AQUI
                                })
                                print(f"  [+] Coluna Estrangeira Mapeada: Arquivo '{arquivo}' -> Aba '{aba_nome}' -> Coluna '{col_name}'")
            except Exception as e:
                print(f"Erro ao ler o arquivo {arquivo}: {e}")

    def ler_fornecedores(self):
        """ Lê a Tabela Pai extraindo a Chave Primária """
        registros = []
        if not os.path.exists(self.base_file):
            raise FileNotFoundError(f"Arquivo base não encontrado: {self.base_file}")
            
        wb = openpyxl.load_workbook(self.base_file)
        
        # Força a leitura na aba correta (ex: "Produto")
        if self.base_sheet in wb.sheetnames:
            aba = wb[self.base_sheet]
        else:
            aba = wb.active
            print(f"  [!] Aviso: Aba '{self.base_sheet}' não encontrada. Usando aba ativa '{aba.title}'.")
        
        header = [str(cell.value).strip().upper() if cell.value else "" for cell in aba[1]]
        col_id = 1
        col_nome = 2
        
        # Encontra a Chave Primária e o Nome (Com blindagem contra a palavra MedIDa)
        for i, h in enumerate(header):
            # Quebra o cabeçalho em palavras isoladas (Ex: "ID PRODUTO" vira ['ID', 'PRODUTO'])
            palavras = h.replace("_", " ").split()
            
            # Só aceita se a palavra inteira for "ID", ignorando o "ID" dentro de outras palavras
            if "ID" in palavras or h == "ID": 
                col_id = i + 1
                
            # Prioriza a coluna que se chama exatamente "NOME"
            if h == "NOME": 
                col_nome = i + 1
            
        if len(header) >= 3 and (header[1] == "ATIVO" or header[1] == "STATUS"):
            col_nome = 3

        for row in aba.iter_rows(min_row=2):
            v_id = row[col_id - 1].value
            v_nome = row[col_nome - 1].value
            if v_id:
                registros.append(Registro(v_id, v_nome))
        
        return registros

    def contar_movimentacoes(self):
        contagem = defaultdict(lambda: defaultdict(int))
        for mapa in self.mapeamento:
            wb = self.workbooks[mapa['arquivo']]
            aba = wb[mapa['aba']]
            col_idx = mapa['col_idx']
            context_name = f"{mapa['arquivo'].replace('.xlsx','')} | {mapa['aba']} | {mapa.get('col_nome', 'Desconhecida')}"
            
            for row in aba.iter_rows(min_row=2):
                val = row[col_idx - 1].value
                if val:
                    val_str = str(val).strip()
                    contagem[val_str][context_name] += 1
        return contagem

    def atualizar_ids(self, migracoes):
        mapa_subst = {str(m.origem): str(m.destino) for m in migracoes}
        for mapa in self.mapeamento:
            wb = self.workbooks[mapa['arquivo']]
            aba = wb[mapa['aba']]
            col_idx = mapa['col_idx']
            
            for row in aba.iter_rows(min_row=2):
                cell = row[col_idx - 1]
                val = cell.value
                if val:
                    val_str = str(val).strip()
                    # Substituição exata de Chave-Valor
                    if val_str in mapa_subst:
                        cell.value = mapa_subst[val_str]

    def validar_migracoes(self, migracoes):
        falhas = []
        ids_origem = {str(m.origem) for m in migracoes}
        for mapa in self.mapeamento:
            wb = self.workbooks[mapa['arquivo']]
            aba = wb[mapa['aba']]
            col_idx = mapa['col_idx']
            
            for row in aba.iter_rows(min_row=2):
                val = row[col_idx - 1].value
                if val and str(val).strip() in ids_origem:
                    falhas.append(str(val).strip())
        return list(set(falhas))

    def salvar_planilhas(self):
        salvos = []
        for arquivo, wb in self.workbooks.items():
            # Separa o caminho da pasta do nome do arquivo real
            pasta, nome_arquivo = os.path.split(arquivo)
            
            # Gruda a tag 'ATUALIZADO_' apenas no nome do arquivo, e depois remonta o caminho
            nome_salvo = os.path.join(pasta, f"ATUALIZADO_{nome_arquivo}")
            
            wb.save(nome_salvo)
            salvos.append(nome_salvo)
        return salvos

    def salvar_base_fornecedores_limpa(self, ids_remover):
        wb = openpyxl.load_workbook(self.base_file)
        if self.base_sheet in wb.sheetnames:
            aba = wb[self.base_sheet]
        else:
            aba = wb.active
        
        header = [str(cell.value).strip().upper() if cell.value else "" for cell in aba[1]]
        col_id = 1
        for i, h in enumerate(header):
            if "ID" in h: 
                col_id = i + 1
                break
        
        linhas_para_deletar = []
        for idx, row in enumerate(aba.iter_rows(min_row=2), start=2):
            val = row[col_id - 1].value
            if val and str(val).strip() in ids_remover:
                linhas_para_deletar.append(idx)
        
        for idx in reversed(linhas_para_deletar):
            aba.delete_rows(idx)
            
        # Mesmo tratamento para a base principal
        pasta, nome_arquivo = os.path.split(self.base_file)
        nome_salvo = os.path.join(pasta, f"LIMPO_{nome_arquivo}")
        
        wb.save(nome_salvo)
        return nome_salvo