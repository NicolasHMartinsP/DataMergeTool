import questionary
from services.excel_service import ExcelService
from services.duplicate_service import DuplicateService
from services.report_service import ReportService
from services.migration_service import MigrationService
from utils import console

def main():
    excel_service = ExcelService()
    duplicate_service = DuplicateService()
    report_service = ReportService()
    migration_service = MigrationService()

    try:
        # ---------------- SPRINT 1 ----------------
        excel_service.abrir_planilhas()
        fornecedores = excel_service.ler_fornecedores()
        contagem = excel_service.contar_movimentacoes()
        grupos_duplicados = duplicate_service.encontrar_duplicados(fornecedores, contagem)
        
        # ---------------- SPRINT 2 (CHECKLIST INTERATIVO) ----------------
        if not grupos_duplicados:
            print("Nenhum fornecedor duplicado encontrado.")
            return

        for grupo in grupos_duplicados:
            itens_pendentes = grupo.duplicados.copy()

            while len(itens_pendentes) > 0:
                console.limpar_tela()
                console.titulo(f"GRUPO: {grupo.nome}")
                print(f"Motivo do Agrupamento: [{grupo.motivo}]")
                print(f"Sugestão Global do Sistema: {grupo.mestre.id} ({grupo.mestre.nome})\n")
                
                # Monta as opções do CHECKLIST
                choices = []
                for f in itens_pendentes:
                    detalhe_lojas = " | ".join([f"{loja}: {qtd}" for loja, qtd in f.movimentacoes_por_loja.items()])
                    choices.append(questionary.Choice(
                        title=f"{f.id:<10} | {f.movimentacoes:<4} notas | {f.nome} ({detalhe_lojas})",
                        value=f
                    ))

                # CHECKLIST: Retorna uma lista de itens selecionados
                selecionados = questionary.checkbox(
                    "Use ESPAÇO para marcar os IDs, e ENTER para confirmar (Deixe vazio para pular o grupo):",
                    choices=choices,
                    style=questionary.Style([
                        ('selected', 'fg:green bold'),
                        ('pointer', 'fg:green bold'),
                        ('highlighted', 'fg:green bold'),
                    ])
                ).ask()

                # Se o usuário não selecionou nada (apertou ENTER direto) ou deu Ctrl+C
                if not selecionados:
                    break
                
                # MENU DE AÇÃO PARA O LOTE SELECIONADO
                print(f"\n>> Você selecionou {len(selecionados)} fornecedor(es).")
                acao = questionary.select(
                    "O que fazer com os itens selecionados?",
                    choices=[
                        questionary.Choice(title=f"[S] Migrar todos para a Sugestão Global ({grupo.mestre.id})", value="S"),
                        questionary.Choice(title="[I] Informar manualmente um ID diferente para este lote", value="I"),
                        questionary.Choice(title="[C] Cancelar seleção e voltar", value="C"),
                    ],
                    style=questionary.Style([('selected', 'fg:cyan bold')])
                ).ask()

                if acao == "C" or acao is None:
                    continue

                dest_id = None
                nome_dest = ""
                qtd_dest = 0

                if acao == "S":
                    dest_id = grupo.mestre.id
                    nome_dest = grupo.mestre.nome
                    qtd_dest = grupo.mestre.movimentacoes
                elif acao == "I":
                    dest_id = input("Digite o ID de destino para este lote (ou ENTER para cancelar): ").strip()
                    if not dest_id:
                        continue
                    
                    # Busca as informações para a tela de confirmação
                    dest_fornecedor = duplicate_service.buscar_por_id(dest_id, fornecedores)
                    if dest_fornecedor:
                        nome_dest = dest_fornecedor.nome
                        qtd_dest = dest_fornecedor.movimentacoes
                    else:
                        nome_dest = "FORNECEDOR NÃO CADASTRADO NA BASE"
                        qtd_dest = 0

                # TELA DE CONFIRMAÇÃO EM LOTE
                total_notas_lote = sum(f.movimentacoes for f in selecionados)
                print(f"\n================ CONFIRMAÇÃO DE LOTE ================")
                print(f"MIGRANDO   : {len(selecionados)} fornecedores (Total de {total_notas_lote} notas)")
                print(f"PARA O ID  : {dest_id} - {nome_dest} (Possui {qtd_dest} notas atualmente)")
                print(f"=====================================================")
                
                confirm = input("Confirmar esta migração em lote? (S/N): ").strip().upper()
                
                if confirm == 'S':
                    for f in selecionados:
                        if f.id != dest_id:
                            migration_service.criar_migracao_individual(f, dest_id)
                        # Remove da lista de pendentes para atualizar o checklist na próxima iteração
                        if f in itens_pendentes:
                            itens_pendentes.remove(f)
                            
                    console.sucesso("Migração em lote registrada com sucesso!")
                else:
                    print("Ação cancelada. Voltando para o checklist...")

                input("\nPressione ENTER para continuar...")

        # ---------------- SPRINT 3 e 4 (BATCH PROCESS) ----------------
        todas_migracoes = migration_service.obter_migracoes()
        
        if todas_migracoes:
            console.limpar_tela()
            console.titulo("EXECUTANDO MIGRAÇÕES")
            print(f"Substituindo {len(todas_migracoes)} IDs nas abas de movimentações...")
            
            excel_service.atualizar_ids(todas_migracoes)
            falhas = excel_service.validar_migracoes(todas_migracoes)
            arquivos_salvos = excel_service.salvar_planilhas()
            
            report_service.mostrar_validacao(falhas, arquivos_salvos, "N/A (Somente Movimentações foram alteradas nesta versão)")
            
        else:
            console.limpar_tela()
            console.sucesso("Nenhuma migração mapeada. Os arquivos originais permanecem inalterados.")

    except Exception as e:
        console.erro(f"Falha na execução do fluxo: {str(e)}")

if __name__ == "__main__":
    main()