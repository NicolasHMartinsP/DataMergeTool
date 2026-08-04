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
        
        # ---------------- SPRINT 2 ----------------
        if not grupos_duplicados:
            print("Nenhum fornecedor duplicado encontrado.")
            return

        for grupo in grupos_duplicados:
            while True:
                report_service.mostrar_relatorio([grupo])
                
                print("O QUE FAZER COM ESTE GRUPO?")
                print("[S] Aceitar a sugestão do sistema")
                print("[I] Informar manualmente outro ID como mestre")
                print("[P] Pular este grupo (não fazer nada)")
                
                escolha = input("\nSua escolha: ").strip().upper()
                
                if escolha == 'S':
                    mestre_id = grupo.mestre.id
                    migration_service.criar_migracoes(grupo, mestre_id)
                    console.sucesso(f"Migrações mapeadas para o mestre {mestre_id}")
                    input("\nPressione ENTER para continuar...")
                    break
                    
                elif escolha == 'I':
                    mestre_id = input("Digite o ID do mestre desejado: ").strip()
                    fornecedor_encontrado = duplicate_service.buscar_por_id(mestre_id, fornecedores)
                    
                    if fornecedor_encontrado:
                        print(f"\n>> O ID pertence a: {fornecedor_encontrado.nome}")
                        confirmacao = input("Deseja confirmar a migração? (S/N): ").strip().upper()
                    else:
                        print(f"\n[AVISO] ID {mestre_id} não encontrado na aba Fornecedores.")
                        confirmacao = input("Deseja forçar a migração para este ID externo mesmo assim? (S/N): ").strip().upper()
                    
                    if confirmacao == 'S':
                        migration_service.criar_migracoes(grupo, mestre_id)
                        console.sucesso(f"Migrações mapeadas para o mestre {mestre_id}")
                        input("\nPressione ENTER para continuar...")
                        break
                    else:
                        print("\nAção cancelada. Retornando às opções do grupo...")
                        input("\nPressione ENTER para continuar...")
                        continue
                        
                elif escolha == 'P':
                    print("Grupo ignorado.")
                    input("\nPressione ENTER para continuar...")
                    break
                    
                else:
                    console.erro("Opção inválida. Tente novamente.")
                    input("\nPressione ENTER para continuar...")
                    continue

        # ---------------- SPRINT 3 e 4 ----------------
        todas_migracoes = migration_service.obter_migracoes()
        
        if todas_migracoes:
            console.limpar_tela()
            console.titulo("EXECUTANDO MIGRAÇÕES E LIMPEZA (SPRINT 4)")
            print(f"Substituindo {len(todas_migracoes)} IDs nas abas de movimentações...")
            
            excel_service.atualizar_ids(todas_migracoes)
            falhas = excel_service.validar_migracoes(todas_migracoes)
            arquivos_salvos = excel_service.salvar_planilhas()
            
            # NOVO: Separa os IDs que morreram (foram substituídos) para limpar a base
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