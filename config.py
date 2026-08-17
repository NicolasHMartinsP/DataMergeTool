# =========================================================================
# DATA MERGE V6.1 - PAINEL DE CONTROLE DA ENGINE
# =========================================================================

# --- TABELAS PAI (CHAVES PRIMÁRIAS - IDENTIDADE REAL) ---
ARQUIVO_BASE_FORNECEDORES = "The Best Almeida.xlsx"
ABA_BASE_FORNECEDORES = "Fornecedores" 

ARQUIVO_BASE_PRODUTOS = "The Best Almeida.xlsx"
ABA_BASE_PRODUTOS = "Produto"

# --- LISTA BRANCA (WHITELIST) DAS TABELAS FILHAS ---
# O script tem bloqueio total e é PROIBIDO de tocar em qualquer aba que não esteja aqui:
ABAS_PERMITIDAS_FORNECEDORES = ["Contas a Pagar", "Notas", "Notas de Compras"]
ABAS_PERMITIDAS_PRODUTOS = ["Itens de Compras", "Notas"]

# --- COLUNAS-ALVO NAS TABELAS FILHAS (CHAVES ESTRANGEIRAS) ---
# O Scanner procurará essas palavras nos cabeçalhos das abas permitidas:
COLUNAS_ALVO_FORNECEDORES = ["Fornecedor", "ID Fornecedor", "Fornecedor_ID", "Cod Fornecedor"]
COLUNAS_ALVO_PRODUTOS = ["Produto", "ID Produto", "Item", "Produto_ID", "Cod Produto"]

# --- MOTOR DE SIMILARIDADE (ASSISTENTE AUTOMÁTICO) ---
SIMILARIDADE_FORNECEDORES = 85  # Mais flexível (tolerância a erros de digitação)
SIMILARIDADE_PRODUTOS = 98      # Rigoroso (Evita agrupar "Água 500ml" com "Água 2L")