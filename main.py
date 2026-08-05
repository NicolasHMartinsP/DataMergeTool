import os
import msvcrt
import json
from services.excel_service import ExcelService
from services.duplicate_service import DuplicateService
from services.report_service import ReportService
from services.migration_service import MigrationService
from utils import console

ARQUIVO_BACKUP = "backup_sessao.json"

def menu_pesquisa_nativo(resultados, termo_busca):
    cursor = 0
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
            if seta == b'H': cursor = max(0, cursor - 1)
            elif seta == b'P': cursor = min(len(opcoes) - 1, cursor + 1)
                
        elif tecla == b'\r': return opcoes[cursor]
        elif tecla == b'\x1b': return None
        elif tecla == b'\x03': raise KeyboardInterrupt

def menu_interativo_nativo(grupo, itens_pendentes, marcados, idx_grupo, total_grupos, total_migracoes):
    cursor = 0
    while True:
        if cursor >= len(itens_pendentes):
            cursor = max(0, len(itens_pendentes) - 1)

        console.limpar_tela()
        # ---------------- HUD DE PROGRESSO ----------------
        print(f"[{'='*73}]")
        print(f" PROGRESSO: Grupo {idx_grupo} de {total_grupos} | Migrações na Sessão: {total_migracoes}")
        print(f"[{'='*73}]\n")
        
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
        print(" [Q] Pausar Sessão (Salva progresso para continuar depois)")
        print("=" * 75)

        tecla = msvcrt.getch()
        
        if tecla in (b'\xe0', b'\x00'):
            seta = msvcrt.getch()
            if seta == b'H': cursor = max(0, cursor - 1)
            elif seta == b'P': cursor = min(len(itens_pendentes) - 1, cursor + 1)
        
        elif tecla == b'\r':
            if itens_pendentes:
                item_id = itens_pendentes[cursor].id
                if item_id in marcados: marcados.remove(item_id)
                else: marcados.add(item_id)
        
        elif tecla.upper() == b'S': return 'S'
        elif tecla.upper() == b'I': return 'I'
        elif tecla.upper() == b'P': return 'P'
        elif tecla.upper() == b'Q': return 'Q'
        elif tecla == b'\x03': raise KeyboardInterrupt


def main():
    excel_service = ExcelService()
    duplicate_service = DuplicateService()
    report_service = ReportService()
    migration_service = MigrationService()
    
    sessao_atual = {}

    try:
        # ---------------- SPRINT 1 ----------------
        excel_service.abrir_planilhas()
        fornecedores = excel_service.ler_fornecedores()
        contagem = excel_service.contar_movimentacoes()
        
        # ---------------- RECUPERAÇÃO DE ESTADO (AUTO-SAVE) ----------------
        if os.path.exists(ARQUIVO_BACKUP):
            try:
                with open(ARQUIVO_BACKUP, "r", encoding="utf-8") as f:
                    sessao_atual = json.load(f)
                    
                if sessao_atual:
                    # Reconstrói a memória do sistema
                    for orig, dest in sessao_atual.items():
                        f_orig = duplicate_service.buscar_por_id(orig, fornecedores)
                        f_dest = duplicate_service.buscar_por_id(dest, fornecedores)
                        if f_orig:
                            migration_service.criar_migracao_individual(f_orig, dest)
                            if f_dest:
                                f_dest.movimentacoes += f_orig.movimentacoes
            except Exception as e:
                console.erro(f"Erro ao ler backup anterior: {e}")

        # Gera os grupos com os fornecedores atualizados
        grupos_duplicados = duplicate_service.encontrar_duplicados(fornecedores, contagem)
        
        # Filtra os fornecedores que JÁ FORAM migrados na sessão anterior
        if sessao_atual:
            for grupo in grupos_duplicados:
                grupo.duplicados = [f for f in grupo.duplicados if f.id not in sessao_atual]
            # Remove os grupos que ficaram vazios ou com apenas 1 item após o filtro
            grupos_duplicados = [g for g in grupos_duplicados if len(g.duplicados) > 1]

        # ---------------- SPRINT 2 (UX DEFINITIVA) ----------------
        if not grupos_duplicados:
            console.sucesso("Não há grupos pendentes. Todas as duplicidades já foram tratadas!")
            # Se já tratou tudo, pula direto para a exportação
        else:
            total_grupos = len(grupos_duplicados)
            pausar_tudo = False

            for idx_grupo, grupo in enumerate(grupos_duplicados, 1):
                if pausar_tudo:
                    break

                itens_pendentes = grupo.duplicados.copy()
                marcados = set()

                while len(itens_pendentes) > 0:
                    acao = menu_interativo_nativo(grupo, itens_pendentes, marcados, idx_grupo, total_grupos, len(sessao_atual))
                    alvos = [f for f in itens_pendentes if f.id in marcados] if marcados else itens_pendentes.copy()

                    if acao == 'Q':
                        console.limpar_tela()
                        print("\nSessão Pausada! O seu progresso atual está salvo com segurança.")
                        print("Ao abrir o programa novamente, ele continuará exatamente deste ponto.\n")
                        gerar = input("Deseja exportar as planilhas parciais agora? (S/N): ").strip().upper()
                        
                        if gerar == 'S':
                            pausar_tudo = True
                            break
                        else:
                            return # Encerra o script totalmente

                    elif acao == 'P':
                        for f in alvos:
                            itens_pendentes.remove(f)
                            if f.id in marcados: marcados.remove(f.id)
                            
                    elif acao == 'S':
                        for f in alvos:
                            if f.id != grupo.mestre.id:
                                migration_service.criar_migracao_individual(f, grupo.mestre.id)
                                grupo.mestre.movimentacoes += f.movimentacoes
                                sessao_atual[f.id] = grupo.mestre.id # Add ao Backup
                                
                            itens_pendentes.remove(f)
                            if f.id in marcados: marcados.remove(f.id)
                            
                        # Grava no arquivo
                        with open(ARQUIVO_BACKUP, "w", encoding="utf-8") as out:
                            json.dump(sessao_atual, out)
                            
                    elif acao == 'I':
                        busca = input("\nDigite o ID exato OU parte do Nome (ENTER p/ cancelar): ").strip()
                        if not busca: continue
                            
                        dest_id = None
                        dest_fornecedor = None
                        
                        dest_fornecedor = duplicate_service.buscar_por_id(busca, fornecedores)
                        if dest_fornecedor:
                            dest_id = dest_fornecedor.id
                            nome_dest = dest_fornecedor.nome
                            qtd_dest = dest_fornecedor.movimentacoes
                        else:
                            resultados = duplicate_service.buscar_por_nome_parcial(busca, fornecedores)
                            if resultados:
                                escolha = menu_pesquisa_nativo(resultados, busca)
                                if escolha is None: continue
                                elif escolha == "EXTERNO":
                                    dest_id = busca
                                    nome_dest = "ID EXTERNO / NÃO CADASTRADO"
                                    qtd_dest = 0
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
                                    nome_dest = "ID EXTERNO"
                                    qtd_dest = 0
                                else:
                                    continue

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
                                        sessao_atual[f.id] = dest_id # Add ao Backup
                                        
                                        if dest_fornecedor:
                                            dest_fornecedor.movimentacoes += f.movimentacoes
                                            
                                    itens_pendentes.remove(f)
                                    if f.id in marcados: marcados.remove(f.id)
                                    
                                # Grava no arquivo
                                with open(ARQUIVO_BACKUP, "w", encoding="utf-8") as out:
                                    json.dump(sessao_atual, out)

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