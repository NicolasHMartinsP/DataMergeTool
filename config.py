import os

# ================= PASTAS =================
PASTA_MOVIMENTACOES = "movimentacoes"
PASTA_CONTAS = "contas"
PASTA_SAIDA = "saida"

# ================= THE BEST ALMEIDA (A BASE PAI) =================
ARQUIVO_FORNECEDORES = "The Best Almeida.xlsx"
ABA_FORNECEDOR = "Fornecedor"
COLUNA_ID = "ID"
COLUNA_NOME = "Nome"

# ================= MAPEAMENTO DE FORNECEDORES =================
COLUNA_FORNECEDOR = "Fornecedor"

# Abas onde devemos substituir o Fornecedor nos arquivos de MOVIMENTAÇÕES
ABAS_MOVIMENTACOES_FORNECEDOR = ["Notas", "Notas de Compras", "Compras"] 

# Abas onde devemos substituir o Fornecedor nos arquivos de CONTAS
ABAS_CONTAS_FORNECEDOR = ["Contas a Pagar", "Contas Pagas", "Contas Fixas"]

# ================= MAPEAMENTO DE PRODUTOS (SPRINT FUTURA) =================
ABAS_ITENS_PRODUTO = ["Itens de Compras"]
COLUNA_PRODUTO = "Produto"