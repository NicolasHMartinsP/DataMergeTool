import os
import msvcrt
from services.excel_service import ExcelService
from services.duplicate_service import DuplicateService
from services.report_service import ReportService
from services.migration_service import MigrationService
from utils import console

def menu_pesquisa_nativo(resultados, termo_busca):
    """
    Renderiza um menu interativo com setas para os resultados da pesquisa.
    """
    cursor = 0
    # Adiciona a opção de usar o termo como ID externo no final da lista
    opcoes = resultados + ["EXTERNO"]

    while True:
        console.limpar_tela()
        console.titulo(f"PESQUISA: '{termo_busca}'")
        print("NAVEGAÇÃO: Setas (Cima/Baixo) | SELEÇÃO: [ENTER] | CANCELAR: [ESC]\n")

        for i, item in enumerate(opcoes):
            cursor_char = " ➜ " if i == cursor else "   "
            if item == "EXTERNO":
                print(f"{cursor_char}[ Usar '{termo_busca}' como um ID Externo / Não Cadastrado ]")
            else:
                print(f"{cursor_char}ID: {item.id:<8} | {item.nome} ({item.movimentacoes} notas)")

        tecla = msvcrt.getch()
        
        if tecla in (b'\xe0', b'\x00'):
            seta = msvcrt.getch()
            if seta == b'H': # Cima
                cursor = max(0, cursor - 1)
            elif seta == b'P': # Baixo
                cursor = min(len(opcoes) - 1, cursor + 1)
                
        elif tecla == b'\r': # ENTER
            return opcoes[cursor]
            
        elif tecla == b'\x1b': # ESC
            return None
            
        elif tecla == b'\x03': # Ctrl+C
            raise KeyboardInterrupt

def menu_interativo_nativo(grupo, itens_pendentes, marcados):
    cursor = 0
    while True:
        if cursor >= len(itens_pendentes):
            cursor = max(0, len(itens_pendentes) - 1)

        console.limpar_tela()
        console.titulo(f"GRUPO: {grupo.nome}")
        print(f"Motivo: [{grupo.motivo}]")
        print(f"Sugestão Global: {grupo.mestre.id} ({grupo.mestre.nome})\n")
        
        print("NAVEGAÇÃO: Setas (Cima/Baixo) | SELEÇÃO: [ENTER]\n")
        
        for i, f in enumerate(itens_pendentes):
            prefixo = "[ X ]" if f.id in marcados else "[   ]"
            cursor_char = " ➜ " if i == cursor else "   "
            detalhe_lojas = " | ".join([f"{loja}: {qtd}" for loja, qtd in f.movimentacoes_por_loja.items()])
            
            linha = f"{cursor_char}{prefixo} {f.id:<8} | {f.movimentacoes:<4} notas | {f.nome} ({detalhe_lojas})"
            print(linha)
            
        print("\n" + "=" * 75)
        qtd = len(marcados)
        alvo_txt = f"nos {qtd} marcados" if qtd > 0 else "em TODOS"
        print(f" ATALHOS DIRETOS (A ação será aplicada {alvo_txt}):")
        print(" [S] Migrar para a Sugestão Global")
        print(" [I] Informar ID / Pesquisar Manualmente")
        print(" [P] Pular / Ignorar")
        print("=" * 75)

        tecla = msvcrt.getch()
        
        if tecla in (b'\xe0', b'\x00'):
            seta = msvcrt.getch()
            if seta == b'H':
                cursor = max(0, cursor - 1)
            elif seta == b'P':
                cursor = min(len(itens_pendentes) - 1, cursor + 1)
        
        elif tecla == b'\r':
            if itens_pendentes:
                item_id = itens_pendentes[cursor].id
                if item_id in marcados:
                    marcados.remove(item_id)
                else:
                    marcados.add(item_id)
        
        elif tecla.upper() == b'S':
            return 'S'
            
        elif tecla.upper() == b'I':
            return 'I'
            
        elif tecla.upper() == b'P':
            return 'P'
            
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
        
        # ---------------- SPRINT 2 (UX DEFINITIVA) ----------------
        if not grupos_duplicados:
            print("Nenhum fornecedor duplicado encontrado.")
            return

        for grupo in grupos_duplicados:
            itens_pendentes = grupo.duplicados.copy()
            marcados = set()

            while len(itens_pendentes) > 0:
                acao = menu_interativo_nativo(grupo, itens_pendentes, marcados)
                alvos = [f for f in itens_pendentes if f.id in marcados] if marcados else itens_pendentes.copy()

                if acao == 'P':
                    for f in alvos:
                        itens_pendentes.remove(f)
                        if f.id in marcados: marcados.remove(f.id)
                        
                elif acao == 'S':
                    for f in alvos:
                        if f.id != grupo.mestre.id:
                            migration_service.criar_migracao_individual(f, grupo.mestre.id)
                            grupo.mestre.movimentacoes += f.movimentacoes
                            
                        itens_pendentes.remove(f)
                        if f.id in marcados: marcados.remove(f.id)
                        
                elif acao == 'I':
                    print(f"\n>> AÇÃO: Informar ID Manual para {len(alvos)} fornecedor(es).")
                    busca = input("Digite o ID exato OU parte do Nome (ENTER p/ cancelar): ").strip()
                    
                    if not busca:
                        continue
                        
                    dest_id = None
                    dest_fornecedor = None
                    nome_dest = ""
                    qtd_dest = 0
                    
                    # 1. Tenta achar exatamente pelo ID primeiro
                    dest_fornecedor = duplicate_service.buscar_por_id(busca, fornecedores)
                    
                    if dest_fornecedor:
                        dest_id = dest_fornecedor.id
                        nome_dest = dest_fornecedor.nome
                        qtd_dest = dest_fornecedor.movimentacoes
                    else:
                        # 2. Pesquisa por nome e chama o NOVO MENU
                        resultados = duplicate_service.buscar_por_nome_parcial(busca, fornecedores)
                        
                        if resultados:
                            escolha = menu_pesquisa_nativo(resultados, busca)
                            
                            if escolha is None:
                                continue # Usuário apertou ESC
                            elif escolha == "EXTERNO":
                                dest_id = busca
                                nome_dest = "ID EXTERNO / NÃO CADASTRADO"
                                qtd_dest = 0
                                dest_fornecedor = None
                            else:
                                dest_fornecedor = escolha
                                dest_id = dest_fornecedor.id
                                nome_dest = dest_fornecedor.nome
                                qtd_dest = dest_fornecedor.movimentacoes
                        else:
                            print(f"\n[AVISO] Nada encontrado com '{busca}'.")
                            usar_externo = input("Deseja forçar o uso como um ID externo? (S/N): ").strip().upper()
                            if usar_externo == 'S':
                                dest_id = busca
                                nome_dest = "ID EXTERNO / NÃO CADASTRADO"
                                qtd_dest = 0
                                dest_fornecedor = None
                            else:
                                continue

                    # 3. Tela de Confirmação
                    if dest_id:
                        total_notas = sum(f.movimentacoes for f in alvos)
                        print(f"\n================ CONFIRMAÇÃO ================")
                        print(f"PARA O ID: {dest_id} - {nome_dest} (Atualmente com {qtd_dest} notas)")
                        print(f"LEVANDO  : {total_notas} notas no total.")
                        print(f"=============================================")
                        
                        confirm = input("Confirmar migração? (S/N): ").strip().upper()
                        if confirm == 'S':
                            for f in alvos:
                                if f.id != dest_id:
                                    migration_service.criar_migracao_individual(f, dest_id)
                                    if dest_fornecedor:
                                        dest_fornecedor.movimentacoes += f.movimentacoes
                                        
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