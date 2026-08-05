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
        
        # ---------------- SPRINT 2 (MENU UNIFICADO) ----------------
        if not grupos_duplicados:
            print("Nenhum fornecedor duplicado encontrado.")
            return

        for grupo in grupos_duplicados:
            itens_pendentes = grupo.duplicados.copy()

            while len(itens_pendentes) > 0:
                console.limpar_tela()
                console.titulo(f"GRUPO: {grupo.nome}")
                print(f"Motivo: [{grupo.motivo}]")
                print(f"Sugestão Global: {grupo.mestre.id} ({grupo.mestre.nome})\n")
                
                # Monta as opções do Menu Unificado
                choices = [
                    questionary.Choice(title="[S] Migrar TODOS abaixo para a Sugestão Global", value="ALL_S"),
                    questionary.Choice(title="[I] Informar um ID manualmente para TODOS abaixo", value="ALL_I"),
                    questionary.Choice(title="[P] Pular o restante do grupo", value="SKIP"),
                    questionary.Separator(line="-" * 60)
                ]
                
                for f in itens_pendentes:
                    detalhe_lojas = " | ".join([f"{loja}: {qtd}" for loja, qtd in f.movimentacoes_por_loja.items()])
                    choices.append(questionary.Choice(
                        title=f"➜ {f.id:<8} | {f.movimentacoes:<4} notas | {f.nome} ({detalhe_lojas})",
                        value=f
                    ))

                # MENU PRINCIPAL
                resposta = questionary.select(
                    "Escolha uma ação global, ou selecione um fornecedor específico abaixo:",
                    choices=choices,
                    style=questionary.Style([('selected', 'fg:green bold')])
                ).ask()

                if resposta == "SKIP" or resposta is None:
                    break
                
                elif resposta == "ALL_S":
                    for f in itens_pendentes:
                        if f.id != grupo.mestre.id:
                            migration_service.criar_migracao_individual(f, grupo.mestre.id)
                    break # Avança para o próximo grupo
                    
                elif resposta == "ALL_I":
                    dest_id = input("Digite o ID de destino para TODOS: ").strip()
                    if dest_id:
                        for f in itens_pendentes:
                            if f.id != dest_id:
                                migration_service.criar_migracao_individual(f, dest_id)
                        break # Avança para o próximo grupo
                    else:
                        continue # Volta se deixar vazio

                else:
                    # USUÁRIO SELECIONOU UM FORNECEDOR ESPECÍFICO
                    item_selecionado = resposta
                    
                    print(f"\n>> Modificando: {item_selecionado.id} ({item_selecionado.nome})")
                    acao_indiv = questionary.select(
                        "O que fazer com ESTE fornecedor?",
                        choices=[
                            questionary.Choice(title=f"[S] Migrar para a Sugestão Global ({grupo.mestre.id})", value="S"),
                            questionary.Choice(title="[I] Informar outro ID manualmente", value="I"),
                            questionary.Choice(title="[V] Voltar (Cancelar)", value="V")
                        ],
                        style=questionary.Style([('selected', 'fg:cyan bold')])
                    ).ask()

                    if acao_indiv == "S":
                        if item_selecionado.id != grupo.mestre.id:
                            migration_service.criar_migracao_individual(item_selecionado, grupo.mestre.id)
                        itens_pendentes.remove(item_selecionado) # Tira da lista pra limpar a tela
                        
                    elif acao_indiv == "I":
                        dest_id = input(f"Digite o ID de destino para {item_selecionado.nome}: ").strip()
                        if dest_id and item_selecionado.id != dest_id:
                            migration_service.criar_migracao_individual(item_selecionado, dest_id)
                            itens_pendentes.remove(item_selecionado)

        # ---------------- SPRINT 3 e 4 (BATCH PROCESS E EXPORTAÇÃO) ----------------
        todas_migracoes = migration_service.obter_migracoes()
        
        if todas_migracoes:
            console.limpar_tela()
            console.titulo("EXECUTANDO MIGRAÇÕES E LIMPEZA")
            print(f"Substituindo {len(todas_migracoes)} IDs nas abas de movimentações...")
            
            excel_service.atualizar_ids(todas_migracoes)
            falhas = excel_service.validar_migracoes(todas_migracoes)
            arquivos_salvos = excel_service.salvar_planilhas()
            
            ids_mortos = [m.origem for m in todas_migracoes]
            arquivo_fornecedores_limpo = excel_service.salvar_base_fornecedores_limpa(ids_mortos)
            
            report_service.mostrar_validacao(falhas, arquivos_salvos, arquivo_fornecedores_limpo)
            
        else:
            console.limpar_tela()
            console.sucesso("Nenhuma migração mapeada. Os arquivos originais permanecem inalterados.")

    except Exception as e:
        console.erro(f"Falha na execução do fluxo: {str(e)}")

if __name__ == "__main__":
    main()