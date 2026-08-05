from typing import List
from models.duplicate_group import DuplicateGroup
from utils import console

class ReportService:
    def mostrar_relatorio(self, grupos: List[DuplicateGroup]):
        console.limpar_tela()
        console.titulo("DATA MERGE TOOL")
        
        if not grupos:
            print("Nenhum fornecedor duplicado encontrado.")
            return

        for grupo in grupos:
            print(f"Fornecedor: {grupo.nome}")
            print(f"Agrupado por: [{grupo.motivo}]\n")
            print(f"{'ID':<14} {'Qtd':<6} {'Rastreio por Loja'}\n")
            
            for f in grupo.duplicados:
                detalhe_lojas = " | ".join([f"{loja}: {qtd}" for loja, qtd in f.movimentacoes_por_loja.items()])
                detalhe_str = f"({detalhe_lojas})" if detalhe_lojas else ""
                
                # Exibe o nome real do cara pra você saber quem ele juntou
                print(f"{f.id:<14} {f.movimentacoes:<6} {f.nome} {detalhe_str}")
                
            print(f"\nSugestão Global:\n{grupo.mestre.id}\n")
            console.separador()
            
    def mostrar_validacao(self, falhas: List[str], arquivos_salvos: List[str], arquivo_fornecedores: str):
        console.separador()
        if falhas:
            console.erro(f"Validação falhou! {len(falhas)} IDs antigos ainda constam nas planilhas:")
            print(falhas)
        else:
            console.sucesso("Validação concluída: 100% dos IDs antigos substituídos.")
            console.sucesso(f"Base de Fornecedores Mestre LIMPA E SALVA em: {arquivo_fornecedores}")
            console.sucesso(f"{len(arquivos_salvos)} planilhas de movimentações salvas:\n")
            for arquivo in arquivos_salvos:
                print(f" -> {arquivo}")