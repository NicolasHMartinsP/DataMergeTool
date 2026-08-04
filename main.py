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
                
            elif escolha == 'I':
                # Sem try-except, pois removemos a restrição de validação
                mestre_id = input("Digite o ID do mestre desejado: ").strip()
                migration_service.criar_migracoes(grupo, mestre_id)
                console.sucesso(f"Migrações mapeadas para o mestre {mestre_id}")
                    
            elif escolha == 'P':
                print("Grupo ignorado.")
            else:
                console.erro("Opção inválida. Pulando grupo por segurança.")
            
            input("\nPressione ENTER para continuar...")

        # ---------------- SPRINT 3 ----------------
        todas_migracoes = migration_service.obter_migracoes()
        
        if todas_migracoes:
            console.limpar_tela()
            console.titulo("EXECUTANDO MIGRAÇÕES (SPRINT 3)")
            print(f"Substituindo {len(todas_migracoes)} IDs nas abas de movimentações...")
            
            # 1. Altera os Pandas DataFrames
            excel_service.atualizar_ids(todas_migracoes)
            
            # 2. Valida a ausência dos IDs antigos
            falhas = excel_service.validar_migracoes(todas_migracoes)
            
            # 3. Salva no disco
            arquivo_salvo = excel_service.salvar_planilhas()
            
            # 4. Reporta o status final
            report_service.mostrar_validacao(falhas, arquivo_salvo)
            
        else:
            console.limpar_tela()
            console.sucesso("Nenhuma migração mapeada. O arquivo original permanece inalterado.")

    except Exception as e:
        console.erro(f"Falha na execução do fluxo: {str(e)}")

if __name__ == "__main__":
    main()