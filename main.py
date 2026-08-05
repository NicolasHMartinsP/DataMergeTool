import os
import msvcrt
from services.excel_service import ExcelService
from services.duplicate_service import DuplicateService
from services.report_service import ReportService
from services.migration_service import MigrationService
from utils import console

def menu_interativo_nativo(grupo, itens_pendentes, marcados):
    """
    Renderiza o menu e captura as teclas instantaneamente, sem precisar de ENTER para os atalhos.
    """
    cursor = 0
    while True:
        # Se a lista diminuir, ajusta o cursor para não quebrar
        if cursor >= len(itens_pendentes):
            cursor = max(0, len(itens_pendentes) - 1)

        console.limpar_tela()
        console.titulo(f"GRUPO: {grupo.nome}")
        print(f"Motivo: [{grupo.motivo}]")
        print(f"Sugestão Global: {grupo.mestre.id} ({grupo.mestre.nome})\n")
        
        print("NAVEGAÇÃO: Setas (Cima/Baixo) | SELEÇÃO: [ENTER]\n")
        
        # Desenha a lista de fornecedores
        for i, f in enumerate(itens_pendentes):
            prefixo = "[ X ]" if f.id in marcados else "[   ]"
            cursor_char = " ➜ " if i == cursor else "   "
            detalhe_lojas = " | ".join([f"{loja}: {qtd}" for loja, qtd in f.movimentacoes_por_loja.items()])
            
            # Destaca a linha onde o cursor está
            linha = f"{cursor_char}{prefixo} {f.id:<8} | {f.movimentacoes:<4} notas | {f.nome} ({detalhe_lojas})"
            print(linha)
            
        # Desenha o rodapé dinâmico
        print("\n" + "=" * 75)
        qtd = len(marcados)
        alvo_txt = f"nos {qtd} marcados" if qtd > 0 else "em TODOS"
        print(f" ATALHOS DIRETOS (A ação será aplicada {alvo_txt}):")
        print(" [S] Migrar para a Sugestão Global")
        print(" [I] Informar ID Manualmente")
        print(" [P] Pular / Ignorar")
        print("=" * 75)

        # Captura a tecla instantaneamente (Sem delay, sem ENTER)
        tecla = msvcrt.getch()
        
        # Identifica setas do teclado (Windows envia dois bytes para setas)
        if tecla in (b'\xe0', b'\x00'):
            seta = msvcrt.getch()
            if seta == b'H': # Seta para Cima
                cursor = max(0, cursor - 1)
            elif seta == b'P': # Seta para Baixo
                cursor = min(len(itens_pendentes) - 1, cursor + 1)
        
        # Tecla ENTER - Marca ou desmarca o item onde a setinha está
        elif tecla == b'\r':
            if itens_pendentes:
                item_id = itens_pendentes[cursor].id
                if item_id in marcados:
                    marcados.remove(item_id)
                else:
                    marcados.add(item_id)
        
        # Tecla S (Maiúscula ou minúscula)
        elif tecla.upper() == b'S':
            return 'S'
            
        # Tecla I (Maiúscula ou minúscula)
        elif tecla.upper() == b'I':
            return 'I'
            
        # Tecla P (Maiúscula ou minúscula)
        elif tecla.upper() == b'P':
            return 'P'
            
        # Tratamento de segurança (Ctrl+C para sair do script)
        elif tecla == b'\x03':
            raise KeyboardInterrupt


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
        
        # ---------------- SPRINT 2 (FLUXO DE ALTA PERFORMANCE) ----------------
        if not grupos_duplicados:
            print("Nenhum fornecedor duplicado encontrado.")
            return

        for grupo in grupos_duplicados:
            itens_pendentes = grupo.duplicados.copy()
            marcados = set()

            while len(itens_pendentes) > 0:
                # O menu assume o controle e só devolve a letra da ação escolhida
                acao = menu_interativo_nativo(grupo, itens_pendentes, marcados)
                
                # Define quem vai sofrer a ação
                alvos = [f for f in itens_pendentes if f.id in marcados] if marcados else itens_pendentes.copy()

                if acao == 'P':
                    # Pular / Ignorar
                    for f in alvos:
                        itens_pendentes.remove(f)
                        if f.id in marcados: marcados.remove(f.id)
                        
                elif acao == 'S':
                    # Migrar para Sugestão Global
                    for f in alvos:
                        if f.id != grupo.mestre.id:
                            migration_service.criar_migracao_individual(f, grupo.mestre.id)
                        itens_pendentes.remove(f)
                        if f.id in marcados: marcados.remove(f.id)
                        
                elif acao == 'I':
                    # Informar ID Manual
                    print(f"\n>> AÇÃO: Informar ID Manual para {len(alvos)} fornecedor(es).")
                    dest_id = input("Digite o ID de destino (ou ENTER para cancelar): ").strip()
                    
                    if dest_id:
                        dest_fornecedor = duplicate_service.buscar_por_id(dest_id, fornecedores)
                        if dest_fornecedor:
                            nome_dest = dest_fornecedor.nome
                            qtd_dest = dest_fornecedor.movimentacoes
                        else:
                            nome_dest = "NÃO CADASTRADO NA BASE"
                            qtd_dest = 0

                        total_notas = sum(f.movimentacoes for f in alvos)
                        print(f"\n================ CONFIRMAÇÃO ================")
                        print(f"PARA O ID: {dest_id} - {nome_dest} (Atualmente com {qtd_dest} notas)")
                        print(f"LEVANDO  : {total_notas} notas no total.")
                        print(f"=============================================")
                        
                        confirm = input("Confirmar? (S/N): ").strip().upper()
                        if confirm == 'S':
                            for f in alvos:
                                if f.id != dest_id:
                                    migration_service.criar_migracao_individual(f, dest_id)
                                itens_pendentes.remove(f)
                                if f.id in marcados: marcados.remove(f.id)

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

    except KeyboardInterrupt:
        console.erro("\nExecução cancelada pelo usuário (Ctrl+C).")
    except Exception as e:
        console.erro(f"\nFalha na execução do fluxo: {str(e)}")

if __name__ == "__main__":
    main()