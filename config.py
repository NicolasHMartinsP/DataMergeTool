

# --- TABELAS PAI (CHAVES PRIMÁRIAS - IDENTIDADE REAL) ---
ARQUIVO_BASE_FORNECEDORES = "The Best Almeida.xlsx"
ABA_BASE_FORNECEDORES = "Fornecedor" 

ARQUIVO_BASE_PRODUTOS = "The Best Almeida.xlsx"
ABA_BASE_PRODUTOS = "Produto"

#WHITELIST
# O script tem bloqueio total e é PROIBIDO de tocar em qualquer aba que não esteja aqui:
ABAS_PERMITIDAS_FORNECEDORES = ["Contas a Pagar", "Notas", "Notas de Compras"]
ABAS_PERMITIDAS_PRODUTOS = ["Itens de Compras", "Notas"]

#  COLUNAS-ALVO NAS TABELAS FILHAS 
# O Scanner procurará essas palavras nos cabeçalhos das abas permitidas:
COLUNAS_ALVO_FORNECEDORES = ["Fornecedor", "ID Fornecedor", "Fornecedor_ID", "Cod Fornecedor"]
COLUNAS_ALVO_PRODUTOS = ["Produto", "ID Produto", "Item", "Produto_ID", "Cod Produto"]

# MOTOR DE SIMILARIDADE 
SIMILARIDADE_FORNECEDORES = 85  # Mais flexível (tolerância a erros de digitação)
SIMILARIDADE_PRODUTOS = 90      # Rigoroso (Evita agrupar "Água 500ml" com "Água 2L")

# CONFIGURAÇÕES DA NUVEM (MODELO HÍBRIDO)

URL_PLANILHA_MESTRE = "https://docs.google.com/spreadsheets/d/13WKDUd5QSiHabRM6L2x6cDdhkUXb2l7TbCdSonzCoQ0/edit?gid=600785414#gid=600785414"

# MOTOR DE INTEGRIDADE REFERENCIAL (Sincronização Cruzada)

# MAPEAMENTO DAS CHAVES
# Nome da coluna que identifica a transação na aba "Contas a Pagar"
COLUNA_LINK_CONTAS = "Nota"

# Nome da coluna que identifica a transação nas abas "Notas" e "Notas de Compras"
COLUNA_LINK_NOTAS = "ID"