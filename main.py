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
        
        # ---------------- SPRINT 2 (NOVO FLUXO INTERATIVO) ----------------
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
                
                # Monta as opções do menu dinamicamente
                choices = []
                for f in itens_pendentes:
                    detalhe_lojas = " | ".join([f"{loja}: {qtd}" for loja, qtd in f.movimentacoes_por_loja.items()])
                    choices.append(questionary.Choice(
                        title=f"{f.id:<10} | {f.movimentacoes:<4} notas | {f.nome} ({detalhe_lojas})",
                        value=f
                    ))
                
                # Opções em lote no final
                choices.append(questionary.Choice(title="\n[✓] Aceitar sugestão global para TODOS os que sobraram na lista", value="ALL"))
                choices.append(questionary.Choice(title="[x] Pular grupo / Ir para o próximo", value="SKIP"))

                # Renderiza o menu verde que navega com setas
                resposta = questionary.select(
                    "Use as setas para escolher um ID para migrar manualmente, ou escolha uma ação:",
                    choices=choices,
                    style=questionary.Style([
                        ('selected', 'fg:green bold'),
                        ('pointer', 'fg:green bold'),
                        ('highlighted', 'fg:green bold'),
                    ])
                ).ask()

                if resposta == "SKIP" or resposta is None:
                    break
                
                elif resposta == "ALL":
                    for f in itens_pendentes:
                        if f.id != grupo.mestre.id:
                            migration_service.criar_migracao_individual(f, grupo.mestre.id)
                    console.sucesso("Fornecedores restantes migrados para o mestre global.")
                    input("\nPressione ENTER para continuar...")
                    break
                    
                else:
                    # USUÁRIO SELECIONOU UM ITEM ESPECÍFICO
                    item_selecionado = resposta
                    print(f"\n>> Você selecionou: {item_selecionado.nome} (ID: {item_selecionado.id})")
                    
                    dest_id = input("Digite o ID de destino para ESTE fornecedor (ou ENTER para cancelar): ").strip()
                    
                    if not dest_id:
                        continue # Volta para o menu se der enter vazio

                    # Busca as informações do destino para a tela de confirmação
                    dest_fornecedor = duplicate_service.buscar_por_id(dest_id, fornecedores)
                    
                    if dest_fornecedor:
                        nome_dest = dest_fornecedor.nome
                        qtd_dest = dest_fornecedor.movimentacoes
                    else:
                        nome_dest = "FORNECEDOR NÃO CADASTRADO NA BASE"
                        qtd_dest = 0

                    # TELA DE CONFIRMAÇÃO EXATA COMO VOCÊ PEDIU
                    print(f"\n================ CONFIRMAÇÃO ================")
                    print(f"MIGRAR DE  : {item_selecionado.id} - {item_selecionado.nome}")
                    print(f"             (Levando {item_selecionado.movimentacoes} notas das abas)")
                    print(f"MIGRAR PARA: {dest_id} - {nome_dest}")
                    print(f"             (Possui {qtd_dest} notas atualmente)")
                    print(f"=============================================")
                    
                    confirm = input("Confirmar esta migração? (S/N): ").strip().upper()
                    
                    if confirm == 'S':
                        if item_selecionado.id != dest_id:
                            migration_service.criar_migracao_individual(item_selecionado, dest_id)
                            itens_pendentes.remove(item_selecionado) # Tira o cara da lista, atualizando o menu!
                            console.sucesso("Migração individual registrada!")
                        else:
                            console.erro("Não é possível migrar um ID para ele mesmo.")
                    else:
                        print("Ação cancelada.")

                    input("\nPressione ENTER para continuar...")

        # ---------------- SPRINT 3 e 4 (BATCH PROCESS) ----------------
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