import os
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
    """ Serializa os objetos complexos em IDs para salvar no disco de forma segura """
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
        print(" [I] Informar ID / Pesquisar Manualmente")
        print(" [P] Pular / Ignorar")
        
        # NOVA LÓGICA VISUAL: Sempre mostra os botões, só avisa se estiver vazio
        aviso_historico = "" if pode_desfazer else " (Indisponível - Histórico Vazio)"
        print(f" [Z] Desfazer última ação{aviso_historico}")
        print(f" [V] Voltar para um Grupo Específico (Rollback){aviso_historico}")
        
        print(" [Q] Pausar Sessão")
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
        elif tecla.upper() == b'Z' and pode_desfazer: return 'Z'
        elif tecla.upper() == b'V' and pode_desfazer: return 'V'
        elif tecla == b'\x03': raise KeyboardInterrupt


def main():
    excel_service = ExcelService()
    duplicate_service = DuplicateService()
    report_service = ReportService()
    migration_service = MigrationService()
    
    sessao_atual = {}
    historico_acoes = []
    ids_processados = set()

    try:
        excel_service.abrir_planilhas()
        fornecedores = excel_service.ler_fornecedores()
        contagem = excel_service.contar_movimentacoes()
        
        grupos_duplicados = duplicate_service.encontrar_duplicados(fornecedores, contagem)
        
        # ---------------- REIDRATAÇÃO DE ESTADO (MÁQUINA DO TEMPO) ----------------
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

                # Reconstrói as migrações no sistema
                for orig, dest in sessao_atual.items():
                    f_orig = duplicate_service.buscar_por_id(orig, fornecedores)
                    f_dest = duplicate_service.buscar_por_id(dest, fornecedores)
                    if f_orig:
                        migration_service.criar_migracao_individual(f_orig, dest)
                        if f_dest:
                            f_dest.movimentacoes += f_orig.movimentacoes
                
                # Reconstrói a linha do tempo e objetos na RAM
                for acao_raw in historico_raw:
                    alvos_objs = []
                    for aid in acao_raw['alvos_ids']:
                        obj = duplicate_service.buscar_por_id(aid, fornecedores)
                        if obj:
                            alvos_objs.append(obj)
                            ids_processados.add(obj.id)
                            
                    dest_obj = duplicate_service.buscar_por_id(acao_raw['dest_fornecedor_id'], fornecedores) if acao_raw['dest_fornecedor_id'] else None
                    
                    historico_acoes.append({
                        'tipo': acao_raw['tipo'],
                        'grupo_idx': acao_raw['grupo_idx'],
                        'alvos': alvos_objs,
                        'dest_fornecedor': dest_obj
                    })
                    
                ids_processados.update(sessao_atual.keys())
                    
            except Exception as e:
                console.erro(f"Erro ao ler backup anterior: {e}")

        # Filtra da tela o que já foi processado
        for grupo in grupos_duplicados:
            grupo.itens_pendentes = [f for f in grupo.duplicados if f.id not in ids_processados]

        # ---------------- MENU E LÓGICA PRINCIPAL ----------------
        if not grupos_duplicados:
            console.sucesso("Não há grupos pendentes. Todas as duplicidades já foram tratadas!")
        else:
            idx_grupo = 0
            pausar_tudo = False

            while idx_grupo < len(grupos_duplicados):
                if pausar_tudo: break
                
                grupo = grupos_duplicados[idx_grupo]
                
                if len(grupo.itens_pendentes) == 0:
                    idx_grupo += 1
                    continue
                
                marcados = set()

                while len(grupo.itens_pendentes) > 0:
                    acao = menu_interativo_nativo(
                        grupo, 
                        grupo.itens_pendentes, 
                        marcados, 
                        idx_grupo + 1, 
                        len(grupos_duplicados), 
                        len(sessao_atual), 
                        len(historico_acoes) > 0
                    )
                    
                    # =============== ROLLBACK LOTE (TECLA V) ===============
                    if acao == 'V':
                        console.limpar_tela()
                        console.titulo("VIAGEM NO TEMPO (RETROCEDER GRUPOS)")
                        grupos_com_historico = sorted(list(set(a['grupo_idx'] for a in historico_acoes)))
                        
                        if not grupos_com_historico:
                            console.erro("Não há histórico suficiente para retroceder.")
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
                            console.erro(f"O Grupo {target_idx + 1} não possui ações registradas no histórico.")
                            time.sleep(2)
                            continue
                        
                        print(f"\nIniciando rollback seguro até o Grupo {target_idx + 1}...")
                        acoes_desfeitas = 0
                        
                        while historico_acoes and historico_acoes[-1]['grupo_idx'] >= target_idx:
                            ultima_acao = historico_acoes.pop()
                            alvos_desfeitos = ultima_acao['alvos']
                            dest_forn = ultima_acao['dest_fornecedor']
                            
                            if ultima_acao['tipo'] in ['S', 'I']:
                                for f in alvos_desfeitos:
                                    migration_service.remover_migracao_individual(f.id)
                                    if f.id in sessao_atual: del sessao_atual[f.id]
                                    if dest_forn and f.id != dest_forn.id:
                                        dest_forn.movimentacoes -= f.movimentacoes
                                        
                            grupo_alvo = grupos_duplicados[ultima_acao['grupo_idx']]
                            for f in alvos_desfeitos:
                                grupo_alvo.itens_pendentes.append(f)
                                
                            acoes_desfeitas += 1
                            
                        salvar_progresso(sessao_atual, historico_acoes)
                        marcados.clear()
                        console.sucesso(f"Rollback concluído! {acoes_desfeitas} ação(ões) desfeita(s).")
                        time.sleep(2)
                        
                        idx_grupo = target_idx
                        break

                    # =============== CTRL+Z (TECLA Z) ===============
                    elif acao == 'Z':
                        ultima_acao = historico_acoes.pop()
                        alvos_desfeitos = ultima_acao['alvos']
                        dest_forn = ultima_acao['dest_fornecedor']
                        
                        if ultima_acao['tipo'] in ['S', 'I']:
                            for f in alvos_desfeitos:
                                migration_service.remover_migracao_individual(f.id)
                                if f.id in sessao_atual: del sessao_atual[f.id]
                                if dest_forn and f.id != dest_forn.id:
                                    dest_forn.movimentacoes -= f.movimentacoes
                                    
                        grupo_alvo = grupos_duplicados[ultima_acao['grupo_idx']]
                        for f in alvos_desfeitos:
                            grupo_alvo.itens_pendentes.append(f)
                            
                        salvar_progresso(sessao_atual, historico_acoes)
                        marcados.clear()
                        
                        nome_acao = "Migração" if ultima_acao['tipo'] in ['S', 'I'] else "Pulo"
                        console.sucesso(f"Desfeito: {nome_acao} de {len(alvos_desfeitos)} item(ns).")
                        time.sleep(1)
                        
                        if ultima_acao['grupo_idx'] < idx_grupo:
                            idx_grupo = ultima_acao['grupo_idx']
                            break
                        else:
                            continue

                    # =============== PROCESSAMENTO NORMAL ===============
                    alvos = [f for f in grupo.itens_pendentes if f.id in marcados] if marcados else grupo.itens_pendentes.copy()

                    if acao == 'Q':
                        console.limpar_tela()
                        print("\nSessão Pausada! Progresso salvo no disco rígido com segurança.")
                        gerar = input("Deseja exportar as planilhas parciais agora? (S/N): ").strip().upper()
                        if gerar == 'S': pausar_tudo = True
                        else: return
                        break

                    elif acao == 'P':
                        for f in alvos:
                            grupo.itens_pendentes.remove(f)
                            if f.id in marcados: marcados.remove(f.id)
                        
                        historico_acoes.append({'tipo': 'P', 'grupo_idx': idx_grupo, 'alvos': alvos.copy(), 'dest_fornecedor': None})
                        salvar_progresso(sessao_atual, historico_acoes)

                    elif acao == 'S':
                        for f in alvos:
                            if f.id != grupo.mestre.id:
                                migration_service.criar_migracao_individual(f, grupo.mestre.id)
                                grupo.mestre.movimentacoes += f.movimentacoes
                                sessao_atual[f.id] = grupo.mestre.id
                                
                            grupo.itens_pendentes.remove(f)
                            if f.id in marcados: marcados.remove(f.id)
                            
                        historico_acoes.append({'tipo': 'S', 'grupo_idx': idx_grupo, 'alvos': alvos.copy(), 'dest_fornecedor': grupo.mestre})
                        salvar_progresso(sessao_atual, historico_acoes)

                    elif acao == 'I':
                        busca = input("\nDigite o ID exato OU parte do Nome (ENTER p/ cancelar): ").strip()
                        if not busca: continue
                            
                        dest_id = None
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
                                    nome_dest = "ID EXTERNO"
                                    qtd_dest = 0
                                else:
                                    dest_fornecedor = escolha
                                    dest_id = dest_fornecedor.id
                                    nome_dest = dest_fornecedor.nome
                                    qtd_dest = dest_fornecedor.movimentacoes
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
                                        if dest_fornecedor:
                                            dest_fornecedor.movimentacoes += f.movimentacoes
                                            
                                    grupo.itens_pendentes.remove(f)
                                    if f.id in marcados: marcados.remove(f.id)
                                    
                                historico_acoes.append({'tipo': 'I', 'grupo_idx': idx_grupo, 'alvos': alvos.copy(), 'dest_fornecedor': dest_fornecedor})
                                salvar_progresso(sessao_atual, historico_acoes)

                if len(grupo.itens_pendentes) == 0:
                    idx_grupo += 1

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
            
            # NOVO: Relatório de Exclusão Física
            with open("RELATORIO_EXCLUSAO.txt", "w", encoding="utf-8") as f:
                f.write("=== FORNECEDORES/PRODUTOS SUBSTITUIDOS ===\n")
                f.write("Estes IDs já não possuem notas e podem ser apagados do sistema:\n\n")
                for m in todas_migracoes:
                    f.write(f"APAGAR ID: {m.origem}  ---> (Movido para: {m.destino})\n")
            
            print(f"\n>> Relatório gerado: RELATORIO_EXCLUSAO.txt")
            
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