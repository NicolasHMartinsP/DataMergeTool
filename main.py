import os
import sys
import msvcrt
import json
import time
from services.excel_service import ExcelService
from services.duplicate_service import DuplicateService
from services.report_service import ReportService
from services.migration_service import MigrationService
from utils import console

ARQUIVO_BACKUP = "backup_sessao.json"

def salvar_progresso(sessao, historico):
    historico_serializado = []
    for acao in historico:
        historico_serializado.append({
            'tipo': acao['tipo'],
            'grupo_idx': acao['grupo_idx'],
            'alvos_ids': [f.id for f in acao['alvos']],
            'dest_fornecedor_id': acao['dest_fornecedor'].id if acao.get('dest_fornecedor') else None
        })
    
    dados = {
        "sessao_atual": sessao,
        "historico": historico_serializado
    }
    with open(ARQUIVO_BACKUP, "w", encoding="utf-8") as out:
        json.dump(dados, out, ensure_ascii=False, indent=4)

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

def menu_interativo_nativo(grupo, itens_pendentes, marcados, idx_grupo, total_grupos, total_migracoes, pode_desfazer):
    cursor = 0
    while True:
        if cursor >= len(itens_pendentes):
            cursor = max(0, len(itens_pendentes) - 1)

        console.limpar_tela()
        print(f"[{'='*73}]")
        print(f" PROGRESSO: Grupo {idx_grupo} de {total_grupos} | Migrações Salvas: {total_migracoes}")
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
        print(" [I] Informar ID / Pesquisar Manualmente (Migrar para outro)")
        print(" [T] Trazer outro Fornecedor perdido para este grupo")
        print(" [P] Pular / Ignorar")
        
        aviso_historico = "" if pode_desfazer else " (Indisponível - Vazio)"
        print(f" [Z] Desfazer última ação{aviso_historico}")
        print(f" [V] Voltar para um Grupo Específico (Rollback){aviso_historico}")
        print(" [Q] Pausar Sessão e Voltar ao Hub")
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
        elif tecla.upper() == b'T': return 'T'
        elif tecla.upper() == b'P': return 'P'
        elif tecla.upper() == b'Q': return 'Q'
        elif tecla.upper() == b'Z' and pode_desfazer: return 'Z'
        elif tecla.upper() == b'V' and pode_desfazer: return 'V'
        elif tecla == b'\x03': raise KeyboardInterrupt

def atualizar_pendencias_grupos(grupos_duplicados, ids_processados):
    """ Garante que itens processados manualmente sumam do assistente automático """
    for grupo in grupos_duplicados:
        grupo.itens_pendentes = [f for f in grupo.duplicados if f.id not in ids_processados]

def main():
    excel_service = ExcelService()
    duplicate_service = DuplicateService()
    report_service = ReportService()
    migration_service = MigrationService()
    
    sessao_atual = {}
    historico_acoes = []
    ids_processados = set()

    try:
        # Carregamento Inicial
        excel_service.abrir_planilhas()
        fornecedores = excel_service.ler_fornecedores()
        contagem = excel_service.contar_movimentacoes()
        grupos_duplicados = duplicate_service.encontrar_duplicados(fornecedores, contagem)
        
        # Reidratação do Disco (Máquina do Tempo)
        if os.path.exists(ARQUIVO_BACKUP):
            try:
                with open(ARQUIVO_BACKUP, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    
                if "sessao_atual" in dados:
                    sessao_atual = dados["sessao_atual"]
                    historico_raw = dados.get("historico", [])
                else:
                    sessao_atual = dados
                    historico_raw = []

                for orig, dest in sessao_atual.items():
                    f_orig = duplicate_service.buscar_por_id(orig, fornecedores)
                    f_dest = duplicate_service.buscar_por_id(dest, fornecedores)
                    if f_orig:
                        migration_service.criar_migracao_individual(f_orig, dest)
                        if f_dest:
                            f_dest.movimentacoes += f_orig.movimentacoes
                
                for acao_raw in historico_raw:
                    alvos_objs = []
                    for aid in acao_raw['alvos_ids']:
                        obj = duplicate_service.buscar_por_id(aid, fornecedores)
                        if obj:
                            alvos_objs.append(obj)
                            ids_processados.add(obj.id)
                            
                    dest_obj = duplicate_service.buscar_por_id(acao_raw['dest_fornecedor_id'], fornecedores) if acao_raw['dest_fornecedor_id'] else None
                    historico_acoes.append({
                        'tipo': acao_raw['tipo'], 'grupo_idx': acao_raw['grupo_idx'], 
                        'alvos': alvos_objs, 'dest_fornecedor': dest_obj
                    })
                    
                ids_processados.update(sessao_atual.keys())
            except Exception as e:
                console.erro(f"Erro ao ler backup anterior: {e}")

        atualizar_pendencias_grupos(grupos_duplicados, ids_processados)

        # =========================================================================
        # O DASHBOARD HUB
        # =========================================================================
        while True:
            console.limpar_tela()
            console.titulo("DATA MERGE TOOL - HUB PRINCIPAL")
            
            pendentes_auto = sum(1 for g in grupos_duplicados if len(g.itens_pendentes) > 0)
            
            print(f" 📦 Migrações na Fila (Prontas para gerar arquivo): {len(sessao_atual)}")
            print(f" 🤖 Grupos Automáticos Pendentes: {pendentes_auto}\n")
            
            print(" [1] 🪄 Iniciar/Continuar Assistente Automático")
            print(" [2] 🎯 Forçar Migração Manual Livre (De ➜ Para)")
            
            status_z = " (Ctrl+Z)" if historico_acoes else " (Indisponível - Histórico Vazio)"
            print(f" [Z] ↩️ Desfazer última ação global{status_z}")
            
            print("\n [E] 🚀 EXECUTAR MIGRAÇÕES E EXPORTAR ARQUIVOS")
            print(" [Q] 🚪 Salvar e Sair (Sem exportar)")
            print("=============================================================")
            
            tecla_hub = msvcrt.getch().upper()

            # --------------------------------------------------------
            # OPÇÃO 1: ASSISTENTE AUTOMÁTICO
            # --------------------------------------------------------
            if tecla_hub == b'1':
                if pendentes_auto == 0:
                    console.sucesso("Não há grupos automáticos pendentes.")
                    time.sleep(2)
                    continue

                idx_grupo = 0
                while idx_grupo < len(grupos_duplicados):
                    grupo = grupos_duplicados[idx_grupo]
                    
                    if len(grupo.itens_pendentes) == 0:
                        idx_grupo += 1
                        continue
                    
                    marcados = set()
                    voltar_pro_hub = False

                    while len(grupo.itens_pendentes) > 0:
                        acao = menu_interativo_nativo(
                            grupo, grupo.itens_pendentes, marcados, 
                            idx_grupo + 1, len(grupos_duplicados), 
                            len(sessao_atual), len(historico_acoes) > 0
                        )
                        
                        if acao == 'V':
                            console.limpar_tela()
                            console.titulo("VIAGEM NO TEMPO (RETROCEDER GRUPOS)")
                            grupos_com_historico = sorted(list(set(a['grupo_idx'] for a in historico_acoes if isinstance(a['grupo_idx'], int))))
                            
                            if not grupos_com_historico:
                                console.erro("Não há histórico de grupos suficientes para retroceder.")
                                time.sleep(2)
                                continue
                                
                            print("Você possui ações reversíveis nos seguintes grupos:\n")
                            for g_idx in grupos_com_historico:
                                g_nome = grupos_duplicados[g_idx].nome
                                print(f"➜ Grupo {g_idx + 1}: {g_nome}")
                                
                            alvo_str = input("\nDigite o NÚMERO do Grupo para o qual deseja voltar (ou ENTER para cancelar): ").strip()
                            if not alvo_str.isdigit(): continue
                                
                            target_idx = int(alvo_str) - 1
                            if target_idx not in grupos_com_historico:
                                console.erro("Grupo inválido.")
                                time.sleep(1)
                                continue
                            
                            acoes_desfeitas = 0
                            while historico_acoes and isinstance(historico_acoes[-1]['grupo_idx'], int) and historico_acoes[-1]['grupo_idx'] >= target_idx:
                                u_acao = historico_acoes.pop()
                                dest_f = u_acao['dest_fornecedor']
                                if u_acao['tipo'] in ['S', 'I']:
                                    for f in u_acao['alvos']:
                                        migration_service.remover_migracao_individual(f.id)
                                        if f.id in sessao_atual: del sessao_atual[f.id]
                                        ids_processados.discard(f.id)
                                        if dest_f and f.id != dest_f.id: dest_f.movimentacoes -= f.movimentacoes
                                elif u_acao['tipo'] == 'P':
                                    for f in u_acao['alvos']: ids_processados.discard(f.id)
                                acoes_desfeitas += 1
                                
                            atualizar_pendencias_grupos(grupos_duplicados, ids_processados)
                            salvar_progresso(sessao_atual, historico_acoes)
                            marcados.clear()
                            console.sucesso(f"Rollback concluído! {acoes_desfeitas} ação(ões) desfeita(s).")
                            time.sleep(2)
                            idx_grupo = target_idx
                            break

                        elif acao == 'Z':
                            u_acao = historico_acoes.pop()
                            dest_f = u_acao['dest_fornecedor']
                            if u_acao['tipo'] in ['S', 'I', 'M']:
                                for f in u_acao['alvos']:
                                    migration_service.remover_migracao_individual(f.id)
                                    if f.id in sessao_atual: del sessao_atual[f.id]
                                    ids_processados.discard(f.id)
                                    if dest_f and f.id != dest_f.id: dest_f.movimentacoes -= f.movimentacoes
                            elif u_acao['tipo'] == 'P':
                                for f in u_acao['alvos']: ids_processados.discard(f.id)
                                
                            atualizar_pendencias_grupos(grupos_duplicados, ids_processados)
                            salvar_progresso(sessao_atual, historico_acoes)
                            marcados.clear()
                            console.sucesso("Desfeito com sucesso!")
                            time.sleep(1)
                            
                            if isinstance(u_acao['grupo_idx'], int) and u_acao['grupo_idx'] < idx_grupo:
                                idx_grupo = u_acao['grupo_idx']
                                break
                            else: continue

                        alvos = [f for f in grupo.itens_pendentes if f.id in marcados] if marcados else grupo.itens_pendentes.copy()

                        if acao == 'Q':
                            voltar_pro_hub = True
                            break

                        elif acao == 'P':
                            for f in alvos: ids_processados.add(f.id)
                            atualizar_pendencias_grupos(grupos_duplicados, ids_processados)
                            historico_acoes.append({'tipo': 'P', 'grupo_idx': idx_grupo, 'alvos': alvos.copy(), 'dest_fornecedor': None})
                            salvar_progresso(sessao_atual, historico_acoes)

                        elif acao == 'S':
                            for f in alvos:
                                if f.id != grupo.mestre.id:
                                    migration_service.criar_migracao_individual(f, grupo.mestre.id)
                                    grupo.mestre.movimentacoes += f.movimentacoes
                                    sessao_atual[f.id] = grupo.mestre.id
                                ids_processados.add(f.id)
                                
                            atualizar_pendencias_grupos(grupos_duplicados, ids_processados)
                            historico_acoes.append({'tipo': 'S', 'grupo_idx': idx_grupo, 'alvos': alvos.copy(), 'dest_fornecedor': grupo.mestre})
                            salvar_progresso(sessao_atual, historico_acoes)

                        elif acao == 'T':
                            busca = input("\nDigite o ID ou parte do Nome para trazer ao grupo (ENTER p/ cancelar): ").strip()
                            if not busca: continue
                            
                            dest_forn = duplicate_service.buscar_por_id(busca, fornecedores)
                            escolha = None
                            
                            if dest_forn:
                                escolha = dest_forn
                            else:
                                resultados = duplicate_service.buscar_por_nome_parcial(busca, fornecedores)
                                if resultados:
                                    escolha = menu_pesquisa_nativo(resultados, busca)
                                    if escolha == "EXTERNO" or escolha is None:
                                        continue
                                else:
                                    console.erro("Nenhum fornecedor encontrado com esse nome/ID.")
                                    time.sleep(1)
                                    continue
                            
                            if escolha.id in ids_processados:
                                console.erro("Aviso: Este ID já foi migrado ou pulado nesta sessão!")
                                time.sleep(2)
                                continue
                                
                            if any(f.id == escolha.id for f in grupo.itens_pendentes):
                                console.aviso("Aviso: Este ID já está na lista deste grupo!")
                                time.sleep(1.5)
                                continue
                                
                            grupo.itens_pendentes.append(escolha)
                            if escolha not in grupo.duplicados:
                                grupo.duplicados.append(escolha)
                                
                            console.sucesso(f"'{escolha.nome}' foi puxado para este grupo!")
                            time.sleep(1)

                        elif acao == 'I':
                            busca = input("\nDigite o ID exato OU parte do Nome (ENTER p/ cancelar): ").strip()
                            if not busca: continue
                                
                            dest_id = None
                            dest_forn = duplicate_service.buscar_por_id(busca, fornecedores)
                            
                            if dest_forn:
                                dest_id = dest_forn.id
                                nome_dest = dest_forn.nome
                                qtd_dest = dest_forn.movimentacoes
                            else:
                                resultados = duplicate_service.buscar_por_nome_parcial(busca, fornecedores)
                                if resultados:
                                    escolha = menu_pesquisa_nativo(resultados, busca)
                                    if escolha is None: continue
                                    elif escolha == "EXTERNO":
                                        dest_id = busca
                                        nome_dest = "ID EXTERNO"
                                        qtd_dest = 0
                                    else:
                                        dest_forn = escolha
                                        dest_id = dest_forn.id
                                        nome_dest = dest_forn.nome
                                        qtd_dest = dest_forn.movimentacoes
                                else:
                                    print(f"\n[AVISO] Nada encontrado com '{busca}'.")
                                    if input("Forçar uso como ID externo? (S/N): ").strip().upper() == 'S':
                                        dest_id = busca
                                        nome_dest = "ID EXTERNO"
                                        qtd_dest = 0
                                    else: continue

                            if dest_id:
                                total_notas = sum(f.movimentacoes for f in alvos)
                                print(f"\n============= CONFIRMAÇÃO =============")
                                print(f"PARA: {dest_id} - {nome_dest} ({qtd_dest} notas atuais)")
                                print(f"LEVANDO: {total_notas} notas no total.")
                                
                                if input("Confirmar migração? (S/N): ").strip().upper() == 'S':
                                    for f in alvos:
                                        if f.id != dest_id:
                                            migration_service.criar_migracao_individual(f, dest_id)
                                            sessao_atual[f.id] = dest_id
                                            if dest_forn: dest_forn.movimentacoes += f.movimentacoes
                                        ids_processados.add(f.id)
                                        
                                    atualizar_pendencias_grupos(grupos_duplicados, ids_processados)
                                    historico_acoes.append({'tipo': 'I', 'grupo_idx': idx_grupo, 'alvos': alvos.copy(), 'dest_fornecedor': dest_forn})
                                    salvar_progresso(sessao_atual, historico_acoes)

                    if voltar_pro_hub:
                        break
                    
                    if len(grupo.itens_pendentes) == 0:
                        idx_grupo += 1

            # --------------------------------------------------------
            # OPÇÃO 2: FORÇAR MIGRAÇÃO MANUAL (O Pulo do Gato)
            # --------------------------------------------------------
            elif tecla_hub == b'2':
                console.limpar_tela()
                console.titulo("MIGRAÇÃO MANUAL LIVRE (DE ➜ PARA)")
                print("PASSO 1: Quem vai PERDER as notas e SUMIR da base? (Origem)")
                busca_origem = input("Digite o Nome ou ID (ENTER p/ cancelar): ").strip()
                if not busca_origem: continue
                
                resultados_orig = duplicate_service.buscar_por_nome_parcial(busca_origem, fornecedores)
                if not resultados_orig:
                    console.erro("Nenhum registro encontrado para a origem.")
                    time.sleep(1)
                    continue
                    
                origem = menu_pesquisa_nativo(resultados_orig, busca_origem)
                if origem == "EXTERNO" or origem is None: continue
                
                if origem.id in ids_processados:
                    console.erro("Este ID já foi migrado ou pulado nesta sessão. Use o Ctrl+Z se precisar alterar.")
                    time.sleep(3)
                    continue

                console.limpar_tela()
                console.titulo("MIGRAÇÃO MANUAL LIVRE (DE ➜ PARA)")
                print(f"ORIGEM SELECIONADA: {origem.id} | {origem.nome} ({origem.movimentacoes} notas)\n")
                
                print("PASSO 2: Quem vai RECEBER as notas e FICAR na base? (Destino)")
                busca_dest = input("Digite o Nome ou ID (ENTER p/ cancelar): ").strip()
                if not busca_dest: continue

                dest_id = None
                dest_forn = duplicate_service.buscar_por_id(busca_dest, fornecedores)
                
                if dest_forn:
                    dest_id = dest_forn.id
                    nome_dest = dest_forn.nome
                else:
                    resultados_dest = duplicate_service.buscar_por_nome_parcial(busca_dest, fornecedores)
                    if resultados_dest:
                        escolha = menu_pesquisa_nativo(resultados_dest, busca_dest)
                        if escolha is None: continue
                        elif escolha == "EXTERNO":
                            dest_id = busca_dest
                            nome_dest = "ID EXTERNO"
                        else:
                            dest_forn = escolha
                            dest_id = dest_forn.id
                            nome_dest = dest_forn.nome
                    else:
                        print(f"\n[AVISO] Nada encontrado com '{busca_dest}'.")
                        if input("Forçar uso como ID externo? (S/N): ").strip().upper() == 'S':
                            dest_id = busca_dest
                            nome_dest = "ID EXTERNO"
                        else: continue
                
                if dest_id:
                    print(f"\n============= CONFIRMAÇÃO =============")
                    print(f"MIGRAR: {origem.id} ({origem.nome})")
                    print(f"PARA  : {dest_id} ({nome_dest})")
                    print(f"TOTAL : Levando {origem.movimentacoes} notas.")
                    
                    if input("\nConfirmar migração manual? (S/N): ").strip().upper() == 'S':
                        if origem.id != dest_id:
                            migration_service.criar_migracao_individual(origem, dest_id)
                            sessao_atual[origem.id] = dest_id
                            ids_processados.add(origem.id)
                            
                            if dest_forn:
                                dest_forn.movimentacoes += origem.movimentacoes
                                
                            atualizar_pendencias_grupos(grupos_duplicados, ids_processados)
                                
                            historico_acoes.append({
                                'tipo': 'M',
                                'grupo_idx': 'MANUAL', 
                                'alvos': [origem], 
                                'dest_fornecedor': dest_forn
                            })
                            salvar_progresso(sessao_atual, historico_acoes)
                            
                            console.sucesso("Migração Manual forçada com sucesso!")
                            time.sleep(1)

            # --------------------------------------------------------
            # OPÇÃO Z: DESFAZER DIRETO DO HUB
            # --------------------------------------------------------
            elif tecla_hub == b'Z' and historico_acoes:
                u_acao = historico_acoes.pop()
                dest_f = u_acao['dest_fornecedor']
                
                if u_acao['tipo'] in ['S', 'I', 'M']:
                    for f in u_acao['alvos']:
                        migration_service.remover_migracao_individual(f.id)
                        if f.id in sessao_atual: del sessao_atual[f.id]
                        ids_processados.discard(f.id)
                        if dest_f and f.id != dest_f.id: dest_f.movimentacoes -= f.movimentacoes
                elif u_acao['tipo'] == 'P':
                    for f in u_acao['alvos']: ids_processados.discard(f.id)
                    
                atualizar_pendencias_grupos(grupos_duplicados, ids_processados)
                salvar_progresso(sessao_atual, historico_acoes)
                
                console.sucesso("Última ação desfeita com sucesso!")
                time.sleep(1)

            # --------------------------------------------------------
            # OPÇÃO E: EXPORTAR
            # --------------------------------------------------------
            elif tecla_hub == b'E':
                todas_migracoes = migration_service.obter_migracoes()
                
                if todas_migracoes:
                    console.limpar_tela()
                    console.titulo("EXECUTANDO MIGRAÇÕES E LIMPEZA")
                    print(f"Substituindo {len(todas_migracoes)} IDs nas abas de movimentações e contas...")
                    
                    excel_service.atualizar_ids(todas_migracoes)
                    falhas = excel_service.validar_migracoes(todas_migracoes)
                    arquivos_salvos = excel_service.salvar_planilhas()
                    
                    ids_mortos = [m.origem for m in todas_migracoes]
                    
                    with open("RELATORIO_EXCLUSAO.txt", "w", encoding="utf-8") as f:
                        f.write("=== FORNECEDORES SUBSTITUIDOS ===\n")
                        f.write("Estes IDs já não possuem notas e podem ser apagados do sistema:\n\n")
                        for m in todas_migracoes:
                            f.write(f"APAGAR ID: {m.origem}  ---> (Movido para: {m.destino})\n")
                    
                    print(f"\n>> Relatório gerado: RELATORIO_EXCLUSAO.txt")
                    
                    arquivo_fornecedores_limpo = excel_service.salvar_base_fornecedores_limpa(ids_mortos)
                    
                    report_service.mostrar_validacao(falhas, arquivos_salvos, arquivo_fornecedores_limpo)
                    sys.exit()
                    
                else:
                    console.limpar_tela()
                    console.sucesso("Nenhuma migração na fila. Os arquivos originais permanecem inalterados.")
                    time.sleep(2)

            # --------------------------------------------------------
            # OPÇÃO Q: SAIR SEGURO
            # --------------------------------------------------------
            elif tecla_hub == b'Q':
                console.limpar_tela()
                console.sucesso("Progresso salvo com segurança em 'backup_sessao.json'. Até mais!")
                sys.exit()

    except KeyboardInterrupt:
        console.erro("\nExecução cancelada pelo usuário (Ctrl+C).")
    except Exception as e:
        console.erro(f"\nFalha na execução do fluxo: {str(e)}")

if __name__ == "__main__":
    main()