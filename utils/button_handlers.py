import time
import sys
import msvcrt
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich import box
from rich.markup import escape

from utils import console as utils_console

class ButtonHandlers:
    def __init__(self, ui_view, state_manager, excel_service, duplicate_service, migration_service, report_service, cross_service, fornecedores, contagem, grupos_duplicados, modo_nome):
        # Injeção de Dependências (O Handler recebe todas as ferramentas que ele precisa para trabalhar)
        self.ui = ui_view 
        self.state = state_manager
        self.excel = excel_service
        self.duplicate = duplicate_service
        self.migration = migration_service
        self.report = report_service
        self.cross = cross_service
        
        # Dados em Memória
        self.fornecedores = fornecedores
        self.contagem = contagem
        self.grupos_duplicados = grupos_duplicados
        self.modo_nome = modo_nome

    # ==========================================
    # BOTÃO 1: ASSISTENTE AUTOMÁTICO
    # ==========================================
    def acao_assistente_automatico(self):
        pendentes_auto = sum(1 for g in self.grupos_duplicados if len(g.itens_pendentes) > 0)
        
        if pendentes_auto == 0:
            self.ui.limpar_tela()
            utils_console.sucesso("\nNão há grupos automáticos pendentes.")
            time.sleep(2)
            return

        idx_grupo = 0
        while idx_grupo < len(self.grupos_duplicados):
            grupo = self.grupos_duplicados[idx_grupo]
            if len(grupo.itens_pendentes) == 0:
                idx_grupo += 1
                continue
            
            marcados = set()
            voltar_pro_hub = False

            while len(grupo.itens_pendentes) > 0:
                # O UI View vai cuidar de desenhar a tela, nós só recebemos a tecla que o usuário apertou
                acao = self.ui.menu_interativo_nativo(grupo, grupo.itens_pendentes, marcados, idx_grupo + 1, len(self.grupos_duplicados), len(self.state.sessao_atual), len(self.state.historico_acoes) > 0)
                
                if acao == 'V':
                    idx_grupo = self._retroceder_grupos()
                    break
                elif acao == 'Z':
                    if self._desfazer_acao_local(idx_grupo):
                        break
                    else: continue
                
                alvos = [f for f in grupo.itens_pendentes if f.id in marcados] if marcados else grupo.itens_pendentes.copy()

                if acao == 'Q':
                    voltar_pro_hub = True
                    break
                elif acao == 'P':
                    self.state.aplicar_pulo_em_lote(alvos, idx_grupo)
                    marcados.clear()
                elif acao == 'S':
                    if self.ui.exibir_confirmacao_migracao(alvos, grupo.mestre.id, grupo.mestre.nome, grupo.mestre, self.modo_nome):
                        self.state.aplicar_migracao_em_lote(alvos, grupo.mestre.id, grupo.mestre, self.migration, 'S', idx_grupo)
                        self.state.atualizar_pendencias_grupos(self.grupos_duplicados) # ATUALIZA A TELA
                        marcados.clear()
                elif acao == 'T':
                    self._trazer_para_grupo(grupo, marcados)
                elif acao == 'I':
                    self._substituir_por_outro(alvos, grupo, marcados, idx_grupo)
                    self.state.atualizar_pendencias_grupos(self.grupos_duplicados) # ATUALIZA A TELA

            if voltar_pro_hub: break
            if len(grupo.itens_pendentes) == 0: idx_grupo += 1

    # ==========================================
    # BOTÃO 2: SUBSTITUIÇÃO MANUAL (De -> Para)
    # ==========================================
    def acao_substituicao_manual(self):
        self.ui.limpar_tela()
        self.ui.console.print(Panel("[bold bright_cyan]SUBSTITUIÇÃO MANUAL LIVRE (DE ➜ PARA)[/bold bright_cyan]", border_style="bright_cyan"))
        self.ui.console.print("[bold bright_white]PASSO 1: Qual ID Antigo será removido das planilhas? (Origem)[/bold bright_white]")
        self.ui.console.print("Digite o Nome ou ID (ENTER p/ cancelar): ", end="")
        busca_origem = input().strip()
        if not busca_origem: return
        
        resultados_orig = self.duplicate.buscar_por_nome_parcial(busca_origem, self.fornecedores)
        if not resultados_orig: return
            
        origem = self.ui.menu_pesquisa_nativo(resultados_orig, busca_origem, self.state.sessao_atual, self.state.ids_processados)
        if origem == "EXTERNO" or origem is None: return
        
        if origem.id in self.state.ids_processados:
            self.ui.console.print("\n[bold bright_yellow][AVISO][/bold bright_yellow] Este ID já foi processado nesta sessão. Use o Ctrl+Z se precisar alterar.")
            time.sleep(2)
            return

        self.ui.limpar_tela()
        self.ui.console.print(Panel("[bold bright_cyan]SUBSTITUIÇÃO MANUAL LIVRE (DE ➜ PARA)[/bold bright_cyan]", border_style="bright_cyan"))
        self.ui.console.print(f"[bold bright_green]ID ANTIGO (SERÁ SUBSTITUÍDO):[/bold bright_green] {origem.id} | {escape(origem.nome)} ({origem.movimentacoes} ocorrências)\n")
        
        self.ui.console.print("[bold bright_white]PASSO 2: Qual será o NOVO ID Oficial nessas linhas? (Destino)[/bold bright_white]")
        self.ui.console.print("Digite o Nome ou ID (ENTER p/ cancelar): ", end="")
        busca_dest = input().strip()
        if not busca_dest: return

        dest_id, nome_dest, dest_forn = self._buscar_destino(busca_dest)
        
        if dest_id:
            if self.ui.exibir_confirmacao_migracao([origem], dest_id, nome_dest, dest_forn, self.modo_nome):
                self.state.aplicar_migracao_em_lote([origem], dest_id, dest_forn, self.migration, 'M', 'MANUAL')

    # ==========================================
    # BOTÃO 3: RAIO-X / PESQUISA
    # ==========================================
    def acao_raiox_pesquisa(self):
        self.ui.limpar_tela()
        self.ui.console.print(Panel(f"[bold bright_yellow]🔍 MODO DE PESQUISA (RAIO-X DE {self.modo_nome})[/bold bright_yellow]", border_style="bright_yellow"))
        self.ui.console.print("[bold bright_white]Qual registro você deseja consultar nas planilhas?[/bold bright_white]")
        self.ui.console.print("Digite o Nome ou ID (ENTER p/ cancelar): ", end="")
        busca = input().strip()
        if not busca: return
        
        resultados = self.duplicate.buscar_por_nome_parcial(busca, self.fornecedores)
        alvo = None
        
        exato = self.duplicate.buscar_por_id(busca, self.fornecedores)
        if exato:
            alvo = exato
        elif resultados:
            escolha = self.ui.menu_pesquisa_nativo(resultados, busca, self.state.sessao_atual, self.state.ids_processados)
            if escolha == "EXTERNO" or escolha is None: return
            alvo = escolha
        else:
            self.ui.console.print(f"\n[bold red][AVISO][/bold red] Nada encontrado na base oficial com '{escape(busca)}'.")
            time.sleep(2)
            return
            
        self.ui.desenhar_tela_raiox(alvo)

    # ==========================================
    # BOTÃO 4: CAÇADOR DE ÓRFÃOS
    # ==========================================
    def acao_cacador_orfaos(self):
        master_ids = {str(f.id).strip().lower() for f in self.fornecedores}
        orfaos = {k: v for k, v in self.contagem.items() if str(k).strip().lower() not in master_ids and str(k).strip() and str(k).lower() != "none"}
        
        if not orfaos:
            self.ui.limpar_tela()
            self.ui.console.print(Panel(f"[bold bright_magenta]👻 CAÇADOR DE ÓRFÃOS ({self.modo_nome}S FANTASMAS)[/bold bright_magenta]", border_style="bright_magenta"))
            utils_console.sucesso("\nParabéns! Não há nenhum ID fantasma nas suas planilhas de movimentação.")
            time.sleep(2)
            return
        
        orfaos_ordenados = sorted(orfaos.items(), key=lambda item: sum(item[1].values()), reverse=True)
        self.ui.paginar_orfaos(orfaos_ordenados, self.modo_nome)

    # ==========================================
    # BOTÃO 5: LIMPAR PESO MORTO
    # ==========================================
    def acao_limpar_peso_morto(self):
        inativos = [f for f in self.fornecedores if f.movimentacoes == 0]
        
        if not inativos:
            self.ui.limpar_tela()
            self.ui.console.print(Panel(f"[bold bright_magenta]🗑️ LIMPEZA DE PESO MORTO ({self.modo_nome}S INATIVOS)[/bold bright_magenta]", border_style="bright_magenta"))
            utils_console.sucesso("\nExcelente! Todos os registros da base oficial possuem movimentações nas planilhas.")
            time.sleep(2)
            return
        
        self.ui.paginar_inativos(inativos, self.modo_nome)

    # ==========================================
    # BOTÃO 6: SINCRONIZADOR CRUZADO
    # ==========================================
    def acao_sincronizador_cruzado(self):
        self.ui.limpar_tela()
        self.ui.console.print(Panel(f"[bold bright_blue]🔗 LENDO MATRIZ RELACIONAL...[/bold bright_blue]", border_style="bright_blue"))
        print("Cruzando chaves primárias entre Contas a Pagar e Notas...")
        
        conflitos = self.cross.escanear_integridade(self.excel.workbooks, self.fornecedores)
        
        if not conflitos:
            utils_console.sucesso("\nIntegridade 100%! Nenhuma quebra encontrada entre as notas e as contas.")
            time.sleep(2)
            return

        pagina_atual = 0
        while conflitos:
            tamanho_pagina = 10
            total_paginas = max(1, (len(conflitos) + tamanho_pagina - 1) // tamanho_pagina)
            if pagina_atual >= total_paginas: pagina_atual = max(0, total_paginas - 1)

            acao = self.ui.paginar_conflitos(conflitos, pagina_atual)

            if acao == 'PROXIMO':
                pagina_atual += 1
            elif acao == 'ANTERIOR':
                pagina_atual -= 1
            elif acao == 'SAIR':
                break
            elif acao == 'EXPORTAR':
                with open("RELATORIO_QUEBRAS.txt", "w", encoding="utf-8") as f_out:
                    f_out.write("=== RELATORIO DE QUEBRAS REFERENCIAIS ===\n")
                    f_out.write("Notas com divergência entre Contas a Pagar e Notas de Compra:\n\n")
                    for c in conflitos:
                        loja = self.ui._limpar_nome_loja(c['conta']['arquivo'])[0]
                        f_out.write(f"LOJA: {loja} | NOTA Nº: {c['id_nota']}\n")
                        f_out.write(f"  -> Contas a Pagar: {c['conta']['val'] or '---'} ({c['st_c']})\n")
                        f_out.write(f"  -> Notas de Compra: {c['nota']['val'] or '---'} ({c['st_n']})\n")
                        f_out.write("-" * 50 + "\n")
                utils_console.sucesso("\nRelatório exportado com sucesso: RELATORIO_QUEBRAS.txt")
                time.sleep(2)

            elif acao == 'RESOLVER':
                # --- FLUXO MODO MICRO PERSISTENTE ---
                while True:
                    # Recalcula as páginas dinamicamente para não bugar a lista quando os itens sumirem
                    tamanho_pagina = 10
                    total_paginas = max(1, (len(conflitos) + tamanho_pagina - 1) // tamanho_pagina)
                    if pagina_atual >= total_paginas: 
                        pagina_atual = max(0, total_paginas - 1)
                    
                    inicio = pagina_atual * tamanho_pagina
                    conflitos_pagina = conflitos[inicio:inicio + tamanho_pagina]

                    if not conflitos_pagina:
                        break # Se zerou tudo nesta visão, volta pro Macro automaticamente

                    acao_lote, alvos = self.ui.menu_resolucao_lote(conflitos_pagina, len(conflitos))
                    
                    if acao_lote == 'Q':
                        break # Sai do modo Micro por vontade do usuário
                        
                    if not alvos:
                        continue 
                        
                    sucesso_count = 0
                    resolvidos_ids = set()
                    
                    if acao_lote == 'I':
                        self.ui.limpar_tela()
                        self.ui.console.print(Panel("[bold bright_cyan]PESQUISAR ID DEFINITIVO PARA O LOTE[/bold bright_cyan]", border_style="bright_cyan"))
                        self.ui.console.print("Digite o ID exato ou Nome (ENTER p/ cancelar): ", end="")
                        busca = input().strip()
                        if not busca: continue
                        
                        id_escolhido = None
                        resultados = self.duplicate.buscar_por_nome_parcial(busca, self.fornecedores)
                        if resultados:
                            escolha = self.ui.menu_pesquisa_nativo(resultados, busca, self.state.sessao_atual, self.state.ids_processados)
                            if escolha and escolha != "EXTERNO":
                                id_escolhido = escolha.id
                            elif escolha == "EXTERNO":
                                id_escolhido = busca
                        else:
                            exato = self.duplicate.buscar_por_id(busca, self.fornecedores)
                            if exato: id_escolhido = exato.id
                            else:
                                self.ui.console.print("\n[bold red]Nenhum ID encontrado.[/bold red]")
                                time.sleep(1)
                                continue
                                
                        if id_escolhido:
                            for c in alvos:
                                self.cross.selar_paz(c, id_escolhido)
                                resolvidos_ids.add(c['id_nota'])
                                sucesso_count += 1
                                
                    elif acao_lote == 'S':
                        for c in alvos:
                            if c['sugestao_id']:
                                self.cross.selar_paz(c, c['sugestao_id'])
                                resolvidos_ids.add(c['id_nota'])
                                sucesso_count += 1
                    
                    elif acao_lote == 'C':
                        for c in alvos:
                            val = c['conta']['val']
                            if val:
                                self.cross.selar_paz(c, val)
                                resolvidos_ids.add(c['id_nota'])
                                sucesso_count += 1
                                
                    elif acao_lote == 'N':
                        for c in alvos:
                            val = c['nota']['val']
                            if val:
                                self.cross.selar_paz(c, val)
                                resolvidos_ids.add(c['id_nota'])
                                sucesso_count += 1
                                
                    if sucesso_count > 0:
                        # ATUALIZA A LISTA OFICIAL (Isso resolve a contagem congelada!)
                        conflitos = [c for c in conflitos if c['id_nota'] not in resolvidos_ids]
                        
                        utils_console.sucesso(f"\n{sucesso_count} nota(s) atualizada(s) e removida(s) com sucesso!")
                        time.sleep(1)
                        
                    if not conflitos:
                        break # Volta para a tela inicial se limpar 100% dos conflitos

    # ==========================================
    # BOTÃO Z: DESFAZER
    # ==========================================
    def acao_desfazer(self):
        if self.state.historico_acoes:
            u_acao = self.state.historico_acoes.pop()
            self.state.reverter_acao(u_acao, self.migration)
            self.state.atualizar_pendencias_grupos(self.grupos_duplicados) # ATUALIZA A TELA
            self.ui.limpar_tela()
            utils_console.sucesso("\nÚltima ação desfeita com sucesso!")
            time.sleep(1)

    # ==========================================
    # BOTÃO E: EXPORTAR/ATUALIZAR EXCEL
    # ==========================================
    def acao_exportar_excel(self):
        todas_migracoes = self.migration.obter_migracoes()
        
        # AGORA O BOTÃO "E" OLHA PARA OS DOIS LUGARES!
        if todas_migracoes or hasattr(self.cross, 'total_resolvidos') and self.cross.total_resolvidos > 0:
            self.ui.limpar_tela()
            self.ui.console.print(Panel(f"[bold bright_green]🚀 ATUALIZANDO EXCEL LOCAIS E GERANDO RELATÓRIO ({self.modo_nome}S)[/bold bright_green]", expand=False))
            
            if todas_migracoes:
                print(f"Buscando e substituindo {len(todas_migracoes)} IDs nas abas permitidas...")
                self.excel.atualizar_ids(todas_migracoes)
                falhas = self.excel.validar_migracoes(todas_migracoes)
            else:
                falhas = []
                print(f"Salvando {self.cross.total_resolvidos} quebras de notas seladas pelo Sincronizador...")
                
            arquivos_salvos = self.excel.salvar_planilhas()
            
            if todas_migracoes:
                with open("RELATORIO_EXCLUSAO.txt", "w", encoding="utf-8") as f:
                    f.write(f"=== {self.modo_nome}S ATUALIZADOS ===\n")
                    f.write("As linhas contendo estes IDs foram atualizadas com sucesso nos arquivos físicos.\n")
                    f.write("ATENÇÃO: Como a base The Best Almeida fica na nuvem, lembre-se de deletar estes IDs manualmente:\n\n")
                    for m in todas_migracoes:
                        f.write(f"ID INATIVO A DELETAR: {m.origem}  ---> (Agora pertencem ao ID: {m.destino})\n")
                
                print(f"\n>> Relatório gerado: RELATORIO_EXCLUSAO.txt")
                self.ui.console.print(Panel("[bold bright_yellow]ATENÇÃO PARA LIMPEZA DA BASE OFICIAL:[/bold bright_yellow]\nUse o RELATORIO_EXCLUSAO.txt como guia para deletar as linhas antigas da nuvem.", border_style="bright_yellow"))
            
            self.report.mostrar_validacao(falhas, arquivos_salvos, None)
            sys.exit()
        else:
            self.ui.limpar_tela()
            utils_console.sucesso("\nNenhuma alteração na fila. Os arquivos do Excel permanecem intocados.")
            time.sleep(2)
            
    # ==========================================
    # BOTÃO Q: SALVAR E SAIR
    # ==========================================
    def acao_salvar_sair(self):
        self.ui.limpar_tela()
        utils_console.sucesso(f"\nProgresso salvo com segurança em '{self.state.arquivo_backup}'. Até mais!")
        sys.exit()

    # ==========================================
    # MÉTODOS INTERNOS DE APOIO (Helpers)
    # ==========================================
    def _retroceder_grupos(self):
        self.ui.limpar_tela()
        self.ui.console.print(Panel("[bold bright_yellow]VIAGEM NO TEMPO (RETROCEDER GRUPOS)[/bold bright_yellow]", border_style="bright_yellow"))
        grupos_com_historico = sorted(list(set(a['grupo_idx'] for a in self.state.historico_acoes if isinstance(a['grupo_idx'], int))))
        
        if not grupos_com_historico:
            self.ui.console.print("\n[bold bright_yellow][AVISO][/bold bright_yellow] Não há histórico para retroceder.")
            time.sleep(2)
            return None
            
        self.ui.console.print("[bold bright_white]Ações reversíveis nos seguintes grupos:[/bold bright_white]\n")
        for g_idx in grupos_com_historico:
            g_nome = self.grupos_duplicados[g_idx].nome
            self.ui.console.print(f" [bold bright_cyan]➜[/bold bright_cyan] Grupo {g_idx + 1}: [bright_white]{escape(g_nome)}[/bright_white]")
            
        self.ui.console.print("\n[bold bright_white]NÚMERO do Grupo para voltar (ENTER cancela): [/bold bright_white]", end="")
        alvo_str = input().strip()
        if not alvo_str.isdigit(): return None
        target_idx = int(alvo_str) - 1
        if target_idx not in grupos_com_historico: return None
        
        acoes_desfeitas = 0
        while self.state.historico_acoes and isinstance(self.state.historico_acoes[-1]['grupo_idx'], int) and self.state.historico_acoes[-1]['grupo_idx'] >= target_idx:
            u_acao = self.state.historico_acoes.pop()
            self.state.reverter_acao(u_acao, self.migration)
            acoes_desfeitas += 1

        self.state.atualizar_pendencias_grupos(self.grupos_duplicados)
        utils_console.sucesso(f"\nRollback concluído! {acoes_desfeitas} ação(ões) desfeita(s).")
        time.sleep(2)
        return target_idx

    def _desfazer_acao_local(self, idx_atual):
        u_acao = self.state.historico_acoes.pop()
        self.state.reverter_acao(u_acao, self.migration)
        self.state.atualizar_pendencias_grupos(self.grupos_duplicados)
        utils_console.sucesso("\nDesfeito com sucesso!")
        time.sleep(1)
        if isinstance(u_acao['grupo_idx'], int) and u_acao['grupo_idx'] < idx_atual:
            return True
        return False

    def _buscar_destino(self, busca):
        dest_forn = self.duplicate.buscar_por_id(busca, self.fornecedores)
        if dest_forn:
            return dest_forn.id, dest_forn.nome, dest_forn
            
        resultados = self.duplicate.buscar_por_nome_parcial(busca, self.fornecedores)
        if resultados:
            escolha = self.ui.menu_pesquisa_nativo(resultados, busca, self.state.sessao_atual, self.state.ids_processados)
            if escolha is None: return None, None, None
            if escolha == "EXTERNO": return busca, "ID EXTERNO", None
            return escolha.id, escolha.nome, escolha
            
        self.ui.console.print(f"\n[bold red][AVISO][/bold red] Nada encontrado com '{escape(busca)}'.")
        self.ui.console.print("[bold bright_white]Forçar uso como ID externo? (S/N): [/bold bright_white]", end="")
        if input().strip().upper() == 'S':
            return busca, "ID EXTERNO", None
        return None, None, None

    def _trazer_para_grupo(self, grupo, marcados):
        self.ui.limpar_tela()
        self.ui.console.print(Panel(f"[bold bright_cyan]TRAZER {self.modo_nome} PARA O GRUPO[/bold bright_cyan]", border_style="bright_cyan"))
        self.ui.console.print("\n[bold bright_cyan]>[/bold bright_cyan] Digite o ID ou parte do Nome para pesquisar (ENTER p/ cancelar): ", end="")
        busca = input().strip()
        if not busca: return
        
        escolhas = []
        dest_forn = self.duplicate.buscar_por_id(busca, self.fornecedores)
        if dest_forn: escolhas = [dest_forn]
        else:
            resultados = self.duplicate.buscar_por_nome_parcial(busca, self.fornecedores)
            if resultados:
                pendentes_ids = {f.id for f in grupo.itens_pendentes}
                escolhas = self.ui.menu_pesquisa_multi(resultados, busca, self.state.sessao_atual, self.state.ids_processados, pendentes_ids)
                if not escolhas: return
            else:
                self.ui.console.print("\n[bold bright_yellow][AVISO][/bold bright_yellow] Nenhum registro encontrado com esse nome/ID.")
                time.sleep(1.5)
                return
        
        adicionados = 0
        for escolha in escolhas:
            if escolha.id in self.state.ids_processados:
                self.ui.console.print(f"\n[bold bright_yellow][AVISO][/bold bright_yellow] O ID {escolha.id} já foi processado nesta sessão!")
                time.sleep(1)
                continue
            if any(f.id == escolha.id for f in grupo.itens_pendentes):
                self.ui.console.print(f"\n[bold bright_yellow][AVISO][/bold bright_yellow] O ID {escolha.id} já está na lista deste grupo!")
                time.sleep(1)
                continue
            grupo.itens_pendentes.append(escolha)
            if escolha not in grupo.duplicados: grupo.duplicados.append(escolha)
            adicionados += 1
            
        if adicionados > 0:
            utils_console.sucesso(f"\n{adicionados} registro(s) puxado(s) para este grupo!")
            time.sleep(1.5)

    def _substituir_por_outro(self, alvos, grupo, marcados, idx_grupo):
        self.ui.limpar_tela()
        self.ui.console.print(Panel("[bold bright_cyan]SUBSTITUIÇÃO SELEÇÃO POR OUTRO ID[/bold bright_cyan]", border_style="bright_cyan"))
        self.ui.console.print("\n[bold bright_cyan]>[/bold bright_cyan] Digite o ID exato OU parte do Nome (ENTER p/ cancelar): ", end="")
        busca = input().strip()
        if not busca: return
            
        dest_id, nome_dest, dest_forn = self._buscar_destino(busca)

        if dest_id:
            if self.ui.exibir_confirmacao_migracao(alvos, dest_id, nome_dest, dest_forn, self.modo_nome):
                self.state.aplicar_migracao_em_lote(alvos, dest_id, dest_forn, self.migration, 'I', idx_grupo)
                marcados.clear()