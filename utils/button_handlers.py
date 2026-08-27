import time
import sys
import msvcrt
from rich.panel import Panel
from rich.markup import escape
from utils import console as utils_console

class ButtonHandlers:
    def __init__(self, ui_view, state_manager, excel_service, duplicate_service, migration_service, report_service, cross_service, records, counts, duplicate_groups, mode_name):
        self.ui = ui_view 
        self.state = state_manager
        self.excel = excel_service
        self.duplicate = duplicate_service
        self.migration = migration_service
        self.report = report_service
        self.cross = cross_service
        self.records = records
        self.counts = counts
        self.duplicate_groups = duplicate_groups
        self.mode_name = mode_name

    def handle_automatic_resolution(self):
        pending = sum(1 for g in self.duplicate_groups if len(g.pending_items) > 0)
        if pending == 0:
            self.ui.clear_screen()
            utils_console.print_success("Não há conflitos automáticos pendentes.")
            time.sleep(2)
            return

        group_idx = 0
        while group_idx < len(self.duplicate_groups):
            group = self.duplicate_groups[group_idx]
            if len(group.pending_items) == 0:
                group_idx += 1
                continue
            
            marked = set()
            return_to_hub = False

            while len(group.pending_items) > 0:
                action = self.ui.interactive_menu(group, group.pending_items, marked, group_idx + 1, len(self.duplicate_groups), len(self.state.current_session), len(self.state.action_history) > 0)
                
                if action == 'V':
                    group_idx = self._rollback_groups()
                    break
                elif action == 'Z':
                    if self._undo_local_action(group_idx): break
                    else: continue
                
                targets = [f for f in group.pending_items if f.id in marked] if marked else group.pending_items.copy()

                if action == 'Q':
                    return_to_hub = True
                    break
                elif action == 'P':
                    self.state.apply_batch_skip(targets, group_idx)
                    marked.clear()
                elif action == 'S':
                    if self.ui.confirm_migration(targets, group.master.id, group.master.name, group.master, self.mode_name):
                        self.state.apply_batch_migration(targets, group.master.id, group.master, self.migration, 'S', group_idx)
                        self.state.update_group_pending_items(self.duplicate_groups)
                        marked.clear()
                elif action == 'T':
                    self._bring_to_group(group, marked)
                elif action == 'I':
                    self._substitute_with_another(targets, group, marked, group_idx)
                    self.state.update_group_pending_items(self.duplicate_groups)

            if return_to_hub: break
            if len(group.pending_items) == 0: group_idx += 1

    def handle_manual_substitution(self):
        self.ui.clear_screen()
        self.ui.console.print(Panel("[bold bright_cyan]SUBSTITUIÇÃO MANUAL LIVRE[/bold bright_cyan]", border_style="bright_cyan"))
        self.ui.console.print("Qual ID Antigo será removido das planilhas? (Origem)\nDigite o Nome ou ID (ENTER p/ cancelar): ", end="")
        search_origin = input().strip()
        if not search_origin: return
        
        results_orig = self.duplicate.search_by_partial_name(search_origin, self.records)
        if not results_orig: return
            
        origin = self.ui.search_menu(results_orig, search_origin, self.state.current_session, self.state.processed_ids)
        if origin == "EXTERNO" or origin is None: return
        
        if origin.id in self.state.processed_ids:
            self.ui.console.print("\n[AVISO] Este ID já foi processado nesta sessão.")
            time.sleep(2)
            return

        self.ui.clear_screen()
        self.ui.console.print(Panel(f"ID ANTIGO: {origin.id} | {escape(origin.name)} ({origin.transactions_count} ocorrências)", title="SUBSTITUIÇÃO MANUAL", border_style="bright_cyan"))
        self.ui.console.print("Qual será o NOVO ID Oficial nessas linhas? (Destino)\nDigite o Nome ou ID (ENTER p/ cancelar): ", end="")
        
        search_dest = input().strip()
        if not search_dest: return

        dest_id, dest_name, dest_entity = self._search_target(search_dest)
        
        if dest_id and self.ui.confirm_migration([origin], dest_id, dest_name, dest_entity, self.mode_name):
            self.state.apply_batch_migration([origin], dest_id, dest_entity, self.migration, 'M', 'MANUAL')

    def handle_search(self):
        term = ""
        while True:
            if not term:
                self.ui.clear_screen()
                self.ui.console.print(Panel(f"MODO DE PESQUISA ({self.mode_name})", border_style="yellow"))
                self.ui.console.print("Qual registro deseja consultar? (ENTER vazio para Voltar): ", end="")
                term = input().strip()
                if not term: return 
            
            results = self.duplicate.search_by_partial_name(term, self.records)
            exact = self.duplicate.find_by_id(term, self.records)
            
            combined = []
            if exact: combined.append(exact)
            for r in results:
                if r not in combined: combined.append(r)
            
            if not combined:
                self.ui.console.print(f"\n[ERRO] Nada encontrado com '{escape(term)}'.")
                time.sleep(1.5)
                term = "" 
                continue
                
            action = self.ui.dynamic_xray_menu(combined, term, self.mode_name)
            if action == 'ESC': return 
            elif action == 'I': term = "" 

    def handle_orphan_audit(self):
        master_ids = {str(f.id).strip().lower() for f in self.records}
        orphans = {k: v for k, v in self.counts.items() if str(k).strip().lower() not in master_ids and str(k).strip().lower() != "none"}
        
        if not orphans:
            self.ui.clear_screen()
            utils_console.print_success("Não há registros órfãos nas planilhas.")
            time.sleep(2)
            return
        
        sorted_orphans = sorted(orphans.items(), key=lambda i: sum(i[1].values()), reverse=True)
        self.ui.paginate_orphans(sorted_orphans, self.mode_name)

    def handle_inactive_cleanup(self):
        inactives = [f for f in self.records if f.transactions_count == 0]
        
        if not inactives:
            self.ui.clear_screen()
            utils_console.print_success("Todos os registros possuem movimentações.")
            time.sleep(2)
            return
        
        self.ui.paginate_inactives(inactives, self.mode_name)

    def handle_cross_sync(self):
        self.ui.clear_screen()
        self.ui.console.print(Panel("LENDO MATRIZ RELACIONAL...", border_style="blue"))
        
        conflicts = self.cross.scan_referential_integrity(self.excel.workbooks, self.records)
        
        if not conflicts:
            utils_console.print_success("Integridade 100%! Nenhuma quebra encontrada.")
            time.sleep(2)
            return

        page = 0
        while conflicts:
            action = self.ui.paginate_conflicts(conflicts, page)

            if action == 'NEXT': page += 1
            elif action == 'PREV': page -= 1
            elif action == 'EXIT': break
            elif action == 'EXPORT':
                with open("RELATORIO_QUEBRAS.txt", "w", encoding="utf-8") as f:
                    for c in conflicts:
                        f.write(f"NOTA: {c['transaction_id']} | Contas: {c['bill']['val']} | Compra: {c['invoice']['val']}\n")
                utils_console.print_success("Relatório salvo.")
                time.sleep(2)
            elif action == 'RESOLVE':
                self._resolve_conflicts_batch(conflicts)

    def handle_undo(self):
        if self.state.action_history:
            action = self.state.action_history.pop()
            self.state.undo_last_action(action, self.migration)
            self.state.update_group_pending_items(self.duplicate_groups)
            self.ui.clear_screen()
            utils_console.print_success("Última ação desfeita.")
            time.sleep(1)

    def handle_export(self):
        migrations = self.migration.get_migrations()
        if migrations or self.cross.resolved_count > 0:
            self.ui.clear_screen()
            self.ui.console.print(Panel("ATUALIZANDO EXCEL E GERANDO RELATÓRIO", border_style="green"))
            
            if migrations:
                self.excel.apply_id_updates(migrations)
                failures = self.excel.validate_migrations(migrations)
            else:
                failures = []
                
            saved_files = self.excel.save_workbooks()
            
            if migrations:
                with open("RELATORIO_EXCLUSAO.txt", "w", encoding="utf-8") as f:
                    for m in migrations:
                        f.write(f"DELETAR: {m.source_id} -> NOVO ID: {m.target_id}\n")
                self.ui.console.print("Guia de exclusão gerado: RELATORIO_EXCLUSAO.txt")
            
            self.report.show_validation(failures, saved_files)
            sys.exit()
        else:
            self.ui.clear_screen()
            utils_console.print_success("Nenhuma alteração pendente.")
            time.sleep(2)
            
    def handle_exit(self):
        self.ui.clear_screen()
        utils_console.print_success(f"Progresso salvo em '{self.state.backup_file}'.")
        sys.exit()

    def _resolve_conflicts_batch(self, conflicts):
        page = 0
        while True:
            size = 10
            pages = max(1, (len(conflicts) + size - 1) // size)
            if page >= pages: page = max(0, pages - 1)
            
            current_page = conflicts[page*size : (page+1)*size]
            if not current_page: break

            action, targets = self.ui.batch_resolution_menu(current_page, len(conflicts))
            if action == 'Q': break
            if not targets: continue 
                
            success_count = 0
            resolved_ids = set()
            
            if action == 'I':
                self.ui.clear_screen()
                self.ui.console.print("Pesquisar ID Definitivo\nDigite o ID ou Nome: ", end="")
                term = input().strip()
                if not term: continue
                
                chosen_id = None
                res = self.duplicate.search_by_partial_name(term, self.records)
                if res:
                    choice = self.ui.search_menu(res, term, self.state.current_session, self.state.processed_ids)
                    if choice and choice != "EXTERNO": chosen_id = choice.id
                    elif choice == "EXTERNO": chosen_id = term
                else:
                    exact = self.duplicate.find_by_id(term, self.records)
                    if exact: chosen_id = exact.id
                    
                if chosen_id:
                    for c in targets:
                        self.cross.apply_resolution(c, chosen_id)
                        resolved_ids.add(c['transaction_id'])
                        success_count += 1
                        
            elif action == 'S':
                for c in targets:
                    if c['suggestion_id']:
                        self.cross.apply_resolution(c, c['suggestion_id'])
                        resolved_ids.add(c['transaction_id'])
                        success_count += 1
            elif action == 'C':
                for c in targets:
                    if c['bill']['val']:
                        self.cross.apply_resolution(c, c['bill']['val'])
                        resolved_ids.add(c['transaction_id'])
                        success_count += 1
            elif action == 'N':
                for c in targets:
                    if c['invoice']['val']:
                        self.cross.apply_resolution(c, c['invoice']['val'])
                        resolved_ids.add(c['transaction_id'])
                        success_count += 1
                        
            if success_count > 0:
                conflicts[:] = [c for c in conflicts if c['transaction_id'] not in resolved_ids]
                utils_console.print_success(f"{success_count} nota(s) resolvida(s)!")
                time.sleep(1)
                
            if not conflicts: break

    def _rollback_groups(self):
        self.ui.clear_screen()
        self.ui.console.print(Panel("RETROCEDER GRUPOS", border_style="yellow"))
        history_groups = sorted(list(set(a['group_idx'] for a in self.state.action_history if isinstance(a['group_idx'], int))))
        
        if not history_groups:
            self.ui.console.print("\n[AVISO] Sem histórico para retroceder.")
            time.sleep(2)
            return None
            
        for g_idx in history_groups:
            self.ui.console.print(f" Grupo {g_idx + 1}: {escape(self.duplicate_groups[g_idx].name)}")
            
        self.ui.console.print("\nNÚMERO do Grupo para voltar (ENTER cancela): ", end="")
        target_str = input().strip()
        if not target_str.isdigit(): return None
        target_idx = int(target_str) - 1
        if target_idx not in history_groups: return None
        
        while self.state.action_history and isinstance(self.state.action_history[-1]['group_idx'], int) and self.state.action_history[-1]['group_idx'] >= target_idx:
            action = self.state.action_history.pop()
            self.state.undo_last_action(action, self.migration)

        self.state.update_group_pending_items(self.duplicate_groups)
        utils_console.print_success("Rollback concluído.")
        time.sleep(1)
        return target_idx

    def _undo_local_action(self, current_idx):
        action = self.state.action_history.pop()
        self.state.undo_last_action(action, self.migration)
        self.state.update_group_pending_items(self.duplicate_groups)
        utils_console.print_success("Desfeito com sucesso.")
        time.sleep(1)
        return isinstance(action['group_idx'], int) and action['group_idx'] < current_idx

    def _search_target(self, term):
        exact = self.duplicate.find_by_id(term, self.records)
        if exact: return exact.id, exact.name, exact
            
        results = self.duplicate.search_by_partial_name(term, self.records)
        if results:
            choice = self.ui.search_menu(results, term, self.state.current_session, self.state.processed_ids)
            if choice is None: return None, None, None
            if choice == "EXTERNO": return term, "ID EXTERNO", None
            return choice.id, choice.name, choice
            
        self.ui.console.print(f"\n[ERRO] Nada encontrado com '{escape(term)}'.")
        self.ui.console.print("Forçar uso como ID externo? (S/N): ", end="")
        if input().strip().upper() == 'S': return term, "ID EXTERNO", None
        return None, None, None

    def _bring_to_group(self, group, marked):
        self.ui.clear_screen()
        self.ui.console.print("Pesquisar registro para agrupar (ENTER cancela): ", end="")
        term = input().strip()
        if not term: return
        
        choices = []
        exact = self.duplicate.find_by_id(term, self.records)
        if exact: choices = [exact]
        else:
            results = self.duplicate.search_by_partial_name(term, self.records)
            if results:
                pending_ids = {f.id for f in group.pending_items}
                choices = self.ui.search_menu(results, term, self.state.current_session, self.state.processed_ids, multi=True, pending_ids=pending_ids)
                if not choices: return
            else:
                self.ui.console.print("\n[AVISO] Nenhum registro encontrado.")
                time.sleep(1.5)
                return
        
        added = 0
        for choice in choices:
            if choice.id in self.state.processed_ids: continue
            if any(f.id == choice.id for f in group.pending_items): continue
            group.pending_items.append(choice)
            if choice not in group.duplicates: group.duplicates.append(choice)
            added += 1
            
        if added > 0:
            utils_console.print_success(f"{added} registro(s) adicionado(s) ao grupo!")
            time.sleep(1)

    def _substitute_with_another(self, targets, group, marked, group_idx):
        self.ui.clear_screen()
        self.ui.console.print("Pesquisar NOVO ID Oficial (ENTER cancela): ", end="")
        term = input().strip()
        if not term: return
            
        dest_id, dest_name, dest_entity = self._search_target(term)
        if dest_id and self.ui.confirm_migration(targets, dest_id, dest_name, dest_entity, self.mode_name):
            self.state.apply_batch_migration(targets, dest_id, dest_entity, self.migration, 'I', group_idx)
            marked.clear()