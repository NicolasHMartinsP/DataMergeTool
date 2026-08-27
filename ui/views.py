import os
import msvcrt
import time
from rich.console import Console, Group
from rich.panel import Panel
from rich.align import Align
from rich.table import Table
from rich import box
from rich.markup import escape
from rich.live import Live
from rich.text import Text
from utils import console as utils_console

class UIView:
    def __init__(self):
        self.console = Console()
        self.logo = """
██████╗  █████╗ ████████╗ █████╗     ███╗   ███╗███████╗██████╗  ██████╗ ███████╗
██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗    ████╗ ████║██╔════╝██╔══██╗██╔════╝ ██╔════╝
██║  ██║███████║   ██║   ███████║    ██╔████╔██║█████╗  ██████╔╝██║  ███╗█████╗  
██║  ██║██╔══██║   ██║   ██╔══██║    ██║╚██╔╝██║██╔══╝  ██╔══██╗██║   ██║██╔══╝  
██████╔╝██║  ██║   ██║   ██║  ██║    ██║ ╚═╝ ██║███████╗██║  ██║╚██████╔╝███████╗
╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝    ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
        """

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def select_operation_mode(self):
        self.clear_screen()
        self.console.print(Align.center(f"[bold bright_cyan]{self.logo}[/bold bright_cyan]"))
        self.console.print(Align.center(Panel("SELECIONE O MODO DE OPERAÇÃO - DATA MERGE v8.0", border_style="bright_cyan")))
        import config
        mode1_name = getattr(config, 'MODE_1_NAME', 'Modo 1').upper()
        mode2_name = getattr(config, 'MODE_2_NAME', 'Modo 2').upper()
        self.console.print(f"\n   [bold bright_cyan]>[/bold bright_cyan] [bold bright_white][ 1 ][/bold bright_white] [bold bright_cyan]Operar com {mode1_name}[/bold bright_cyan]")
        self.console.print(f"   [bold bright_magenta]>[/bold bright_magenta] [bold bright_white][ 2 ][/bold bright_white] [bold bright_magenta]Operar com {mode2_name}[/bold bright_magenta]")
        self.console.print("\n   [bold bright_white]Escolha (1 ou 2): [/bold bright_white]", end="")
        
        while True:
            key = msvcrt.getch()
            if key == b'1': return 1
            elif key == b'2': return 2
            elif key == b'\x03': raise KeyboardInterrupt

    def render_hub_ui(self, pending_count, session_length, has_history, mode_name):
        self.clear_screen()
        self.console.print(Align.center(f"[bold bright_cyan]{self.logo}[/bold bright_cyan]"))
        
        import config
        mode1_name = getattr(config, 'MODE_1_NAME', 'Modo 1').upper()
        color = "bright_cyan" if mode_name == mode1_name else "bright_magenta"
        
        status_text = (
            f"  [white]Substituições Pendentes:[/white] [bold bright_green]{session_length}[/bold bright_green]  \n"
            f"  [white]Conflitos a Resolver:[/white] [bold bright_yellow]{pending_count}[/bold bright_yellow]  "
        )
        self.console.print(Align.center(Panel(status_text, title=f"[bold bright_white] DATA MERGE v8.0 - {mode_name} [/bold bright_white]", border_style=color)))
        
        options = [
            ("1", "Resolução Automática", "Inicia o tratamento de duplicados.", "bright_cyan"),
            ("2", "Substituição Manual", "Substitui um ID antigo por um oficial.", "bright_cyan"),
            ("3", "Pesquisar Registro", "Consulta onde um registro está nas planilhas.", "bright_yellow"),
            ("4", "Auditoria de Órfãos", "Auditoria de IDs lançados que não existem na base.", "bright_magenta"),
            ("5", "Remoção de Inativos", "Auditoria de itens cadastrados nunca usados.", "bright_magenta"),
            ("6", "Sincronização Referencial", "Cruza Contas a Pagar e Notas de Compra.", "bright_blue"),
            ("Z", "Desfazer Ação", "Desfaz a última substituição.", "bright_cyan"),
            ("E", "Atualizar Planilhas", "Aplica as substituições nas movimentações.", "bright_green"),
            ("Q", "Salvar e Sair", "Salva o progresso e encerra.", "bright_red")
        ]
        
        self.console.print()
        for key, title, desc, clr in options:
            if not has_history and key == "Z":
                self.console.print(f"   [dim]> [ {key} ] {title} - {desc} (Histórico Vazio)[/dim]")
            else:
                self.console.print(f"   [bold {clr}]>[/bold {clr}] [bold bright_white][ {key} ][/bold bright_white] [bold {clr}]{title}[/bold {clr}] - [dim white]{desc}[/dim white]")
                
        self.console.print(f"\n   [bold {color}]>[/bold {color}] [blink]Aguardando comando...[/blink] ", end="")

    def _clean_store_name(self, raw_name):
        parts = raw_name.split(" | ")
        if len(parts) == 3:
            path, sheet, col = parts
            store = os.path.basename(path).replace("Movimentações - ", "").replace("Contas a Pagar - ", "").strip()
            return store, sheet, col
        store = os.path.basename(raw_name).replace(".xlsx", "").strip()
        return store, "-", "-"

    def interactive_menu(self, group, pending_items, marked, current_idx, total_groups, total_migrations, can_undo):
        self.clear_screen()
        cursor = 0

        def render_layout(pos, sel_set):
            table = Table(show_header=True, header_style="bold bright_magenta", box=box.ROUNDED, expand=True)
            table.add_column("Sel", justify="center")
            table.add_column("ID Antigo")
            table.add_column("Ocorrências", justify="right")
            table.add_column("Nome do Registro")
            
            for i, item in enumerate(pending_items):
                is_sel = item.id in sel_set
                is_cur = i == pos
                prefix = "[bold bright_cyan]>[/] " if is_cur else "  "
                box_char = "[bold bright_green][X][/]" if is_sel else "[dim][ ][/]"
                style = "bold bright_white" if is_cur else ("bright_green" if is_sel else "white")
                table.add_row(f"{prefix}{box_char}", f"[{style}]{item.id}[/]", f"[{style}]{item.transactions_count}[/]", f"[{style}]{escape(item.name)}[/]")
                
            panel_info = Panel(
                f"[bold bright_yellow]Motivo:[/bold bright_yellow] {escape(group.reason)}\n[bold bright_green]ID Oficial Sugerido:[/bold bright_green] {group.master.id} ({escape(group.master.name)})",
                title=f"[bold bright_cyan]GRUPO DE CONFLITO: {escape(group.name)}[/bold bright_cyan]", border_style="bright_cyan"
            )
            
            shortcuts = "[S]ubstituir | [I]nformar Manual | [T]razer Outro | [P]ular | [Z]Desfazer | [V]oltar | [Q]Sair"
            return Group(
                Panel(Align.center(f"Progresso: Grupo {current_idx} de {total_groups} | Substituições: {total_migrations}"), border_style="dim white"),
                panel_info, table, Panel(Align.center(shortcuts), border_style="dim white")
            )

        with Live(render_layout(cursor, marked), console=self.console, auto_refresh=False) as live:
            while True:
                if cursor >= len(pending_items): cursor = max(0, len(pending_items) - 1)
                live.update(render_layout(cursor, marked), refresh=True)
                key = msvcrt.getch()
                if key in (b'\xe0', b'\x00'):
                    arrow = msvcrt.getch()
                    if arrow == b'H': cursor = max(0, cursor - 1)
                    elif arrow == b'P': cursor = min(len(pending_items) - 1, cursor + 1)
                elif key == b'\r':
                    if pending_items:
                        item_id = pending_items[cursor].id
                        marked.remove(item_id) if item_id in marked else marked.add(item_id)
                elif key.upper() in [b'S', b'I', b'T', b'P', b'Q']: return key.upper().decode('utf-8')
                elif key.upper() in [b'Z', b'V'] and can_undo: return key.upper().decode('utf-8')
                elif key == b'\x03': raise KeyboardInterrupt

    def search_menu(self, results, term, current_session, processed_ids, multi=False, pending_ids=None):
        self.clear_screen()
        cursor = 0
        marked = set()
        options = results if multi else results + ["EXTERNO"]

        def render_layout(pos, sel_set):
            table = Table(show_header=True, header_style="bold bright_magenta", box=box.ROUNDED, expand=True)
            table.add_column("Sel" if multi else "->", justify="center")
            table.add_column("Status")
            table.add_column("ID")
            table.add_column("Nome")
            table.add_column("Ocorrências", justify="right")

            for i, item in enumerate(options):
                is_cur = i == pos
                prefix = "[bold bright_cyan]>[/]" if is_cur else " "
                
                if item == "EXTERNO":
                    table.add_row(prefix, "-", "-", f"Usar '{escape(term)}' como ID Externo", "-")
                else:
                    status = "[dim white]INTACTO[/]"
                    if item.id in current_session: status = f"[bold red]SUBSTITUÍDO ({current_session[item.id]})[/]"
                    elif item.id in processed_ids: status = "[bold yellow]PULADO[/]"
                    
                    sel = ""
                    if multi:
                        in_group = pending_ids and item.id in pending_ids
                        if in_group: sel = "[dim blue][G][/]"
                        elif item.id in sel_set: sel = "[bold green][X][/]"
                        else: sel = "[dim][ ][/]"
                        
                    style = "bold white" if is_cur else ("bright_green" if item.id in sel_set else "white")
                    table.add_row(f"{prefix} {sel}", status, f"[{style}]{item.id}[/]", f"[{style}]{escape(item.name)}[/]", f"[{style}]{item.transactions_count}[/]")

            title = f"PESQUISA MÚLTIPLA" if multi else "PESQUISA DE ID OFICIAL"
            footer = "ENTER: Marcar | C: Confirmar | ESC: Cancelar" if multi else "ENTER: Selecionar | ESC: Cancelar"
            return Group(
                Panel(f"[bold bright_cyan]{title}:[/bold bright_cyan] '{escape(term)}'", border_style="bright_cyan"),
                table, Align.center(f"[dim]{footer}[/dim]")
            )

        with Live(render_layout(cursor, marked), console=self.console, auto_refresh=False) as live:
            while True:
                live.update(render_layout(cursor, marked), refresh=True)
                key = msvcrt.getch()
                if key in (b'\xe0', b'\x00'):
                    arrow = msvcrt.getch()
                    if arrow == b'H': cursor = max(0, cursor - 1)
                    elif arrow == b'P': cursor = min(len(options) - 1, cursor + 1)
                elif key == b'\r': 
                    if multi:
                        item_id = options[cursor].id
                        if not pending_ids or item_id not in pending_ids:
                            marked.remove(item_id) if item_id in marked else marked.add(item_id)
                    else: return options[cursor]
                elif multi and key.upper() == b'C': return [r for r in results if r.id in marked]
                elif key == b'\x1b': return [] if multi else None
                elif key == b'\x03': raise KeyboardInterrupt

    def confirm_migration(self, targets, dest_id, dest_name, dest_entity, mode_name):
        self.clear_screen()
        total_moved = sum(t.transactions_count for t in targets if t.id != dest_id)
        current = dest_entity.transactions_count if dest_entity else 0
        
        self.console.print(Panel(
            f"[bold white]ID DESTINO:[/bold white] [bright_yellow]{dest_id}[/bright_yellow] - {escape(dest_name)}\n"
            f"[bold white]Impacto:[/bold white] {current} -> [bold bright_green]{current + total_moved}[/bold bright_green] ocorrências.\n\n"
            f"[dim]ENTER para confirmar | ESC para cancelar[/dim]", 
            title="REVISÃO DE IMPACTO", border_style="bright_cyan"
        ))
        
        while True:
            k = msvcrt.getch()
            if k == b'\r': return True
            if k == b'\x1b': return False

    def dynamic_xray_menu(self, results, term, mode_name):
        self.clear_screen()
        cursor = 0

        def render_layout(pos):
            table = Table(show_header=True, header_style="bold yellow", box=box.ROUNDED, expand=True)
            table.add_column("->")
            table.add_column("ID")
            table.add_column("Nome")
            table.add_column("Ocorrências", justify="right")
            
            for i, item in enumerate(results):
                prefix = "[bold cyan]>[/]" if i == pos else " "
                style = "bold white" if i == pos else "dim white"
                table.add_row(prefix, f"[{style}]{item.id}[/]", f"[{style}]{escape(item.name)}[/]", str(item.transactions_count))

            target = results[pos]
            details = Table(show_header=True, header_style="dim cyan", box=box.SIMPLE_HEAD, expand=True)
            details.add_column("Loja")
            details.add_column("Aba")
            details.add_column("Coluna")
            details.add_column("Qtd", justify="right")
            
            if target.transactions_count > 0:
                summary = {}
                for loc, qty in target.transactions_by_store.items():
                    s, a, c = self._clean_store_name(loc)
                    summary[(s,a,c)] = summary.get((s,a,c), 0) + qty
                for (s, a, c), qty in sorted(summary.items()):
                    details.add_row(escape(s), escape(a), escape(c), str(qty))
            else:
                details.add_row("Sem dados", "-", "-", "0")

            layout = Table.grid(expand=True)
            layout.add_column(ratio=5)
            layout.add_column(ratio=5)
            layout.add_row(table, Panel(details, title="Detalhes do ID", border_style="cyan"))

            return Group(Panel(f"RESULTADOS PARA: '{escape(term)}'", border_style="yellow"), layout, Align.center("[I] Pesquisar Novo | [ESC] Sair"))

        with Live(render_layout(cursor), console=self.console, auto_refresh=False) as live:
            while True:
                live.update(render_layout(cursor), refresh=True)
                k = msvcrt.getch()
                if k in (b'\xe0', b'\x00'):
                    arr = msvcrt.getch()
                    if arr == b'H': cursor = max(0, cursor - 1)
                    elif arr == b'P': cursor = min(len(results) - 1, cursor + 1)
                elif k.upper() == b'I': return 'I'
                elif k in (b'\x1b', b'\x08'): return 'ESC'
                elif k == b'\x03': raise KeyboardInterrupt

    def paginate_orphans(self, orphans, mode_name):
        page = 0
        size = 15
        pages = max(1, (len(orphans) + size - 1) // size)
        
        while True:
            self.clear_screen()
            self.console.print(Panel(f"AUDITORIA DE ÓRFÃOS", border_style="magenta"))
            
            t = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED, expand=True)
            t.add_column("ID Órfão", style="yellow")
            t.add_column("Ocorrências", justify="right")
            
            for o_id, locs in orphans[page*size : (page+1)*size]:
                t.add_row(escape(str(o_id)), str(sum(locs.values())))
                
            self.console.print(t)
            self.console.print(f"Página {page+1} de {pages} | Total: {len(orphans)} órfãos\n")
            self.console.print("[N] Próximo | [A] Anterior | [E] Exportar TXT | [Q] Voltar")
            
            k = msvcrt.getch().upper()
            if k in (b'N', b'P') and page < pages - 1: page += 1
            elif k in (b'A', b'V') and page > 0: page -= 1
            elif k == b'E':
                with open("RELATORIO_ORFAOS.txt", "w", encoding="utf-8") as f:
                    for o_id, locs in orphans: f.write(f"{o_id}: {sum(locs.values())} ocorrencias\n")
                utils_console.print_success("Relatório salvo.")
                time.sleep(1)
            elif k in (b'Q', b'\x1b'): break

    def paginate_inactives(self, inactives, mode_name):
        page = 0
        size = 15
        pages = max(1, (len(inactives) + size - 1) // size)
        
        while True:
            self.clear_screen()
            self.console.print(Panel("REMOÇÃO DE INATIVOS", border_style="magenta"))
            
            t = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED, expand=True)
            t.add_column("ID Oficial", style="yellow")
            t.add_column("Nome", style="white")
            
            for item in inactives[page*size : (page+1)*size]:
                t.add_row(escape(item.id), escape(item.name))
                
            self.console.print(t)
            self.console.print(f"Página {page+1} de {pages} | Total: {len(inactives)} inativos\n")
            self.console.print("[N] Próximo | [A] Anterior | [E] Exportar TXT | [Q] Voltar")
            
            k = msvcrt.getch().upper()
            if k in (b'N', b'P') and page < pages - 1: page += 1
            elif k in (b'A', b'V') and page > 0: page -= 1
            elif k == b'E':
                with open("RELATORIO_INATIVOS.txt", "w", encoding="utf-8") as f:
                    for item in inactives: f.write(f"{item.id} - {item.name}\n")
                utils_console.print_success("Relatório salvo.")
                time.sleep(1)
            elif k in (b'Q', b'\x1b'): break

    def paginate_conflicts(self, conflicts, page):
        size = 10
        pages = max(1, (len(conflicts) + size - 1) // size)
        self.clear_screen()
        
        t = Table(show_header=True, header_style="bold blue", box=box.ROUNDED, expand=True)
        t.add_column("Nota", style="yellow")
        t.add_column("Contas a Pagar")
        t.add_column("Notas de Compra")
        t.add_column("Ação Sugerida", style="green")
        
        for c in conflicts[page*size : (page+1)*size]:
            t.add_row(escape(str(c['transaction_id'])), escape(c['bill']['val']), escape(c['invoice']['val']), escape(str(c['suggestion_id'] or "Manual")))
            
        self.console.print(Panel("INTEGRIDADE REFERENCIAL", border_style="blue"))
        self.console.print(t)
        self.console.print(f"Página {page+1} de {pages} | Total: {len(conflicts)}\n")
        self.console.print("[N] Próximo | [A] Anterior | [R] Resolver | [E] Exportar | [Q] Voltar")
        
        while True:
            k = msvcrt.getch().upper()
            if k in (b'N', b'P') and page < pages - 1: return 'NEXT'
            elif k in (b'A', b'V') and page > 0: return 'PREV'
            elif k == b'R': return 'RESOLVE'
            elif k == b'E': return 'EXPORT'
            elif k in (b'Q', b'\x1b'): return 'EXIT'

    def show_critical_error(self, traceback_msg):
        self.clear_screen()
        self.console.print(Panel(f"ERRO CRÍTICO\n{traceback_msg}", border_style="red"))

    def batch_resolution_menu(self, conflicts_page, remaining):
        self.clear_screen()
        cursor = 0
        marked = set()

        def render_layout(pos, sel_set):
            t = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED, expand=True)
            t.add_column("Sel")
            t.add_column("Nota")
            t.add_column("Contas")
            t.add_column("Notas de Compra")
            
            for i, c in enumerate(conflicts_page):
                is_cur = i == pos
                is_sel = c['transaction_id'] in sel_set
                prefix = "[cyan]>[/]" if is_cur else " "
                sel = "[green][X][/]" if is_sel else "[dim][ ][/]"
                style = "bold white" if is_cur else "white"
                t.add_row(f"{prefix}{sel}", f"[{style}]{c['transaction_id']}[/]", f"[{style}]{c['bill']['val']}[/]", f"[{style}]{c['invoice']['val']}[/]")
                
            return Group(
                Panel(f"RESOLUÇÃO EM LOTE - Restantes: {remaining}", border_style="blue"),
                t, Align.center("[S] Sugestão | [C] Forçar Contas | [N] Forçar Notas | [I] Manual | [Q] Sair")
            )

        with Live(render_layout(cursor, marked), console=self.console, auto_refresh=False) as live:
            while True:
                if cursor >= len(conflicts_page): cursor = max(0, len(conflicts_page) - 1)
                live.update(render_layout(cursor, marked), refresh=True)
                k = msvcrt.getch()
                if k in (b'\xe0', b'\x00'):
                    arr = msvcrt.getch()
                    if arr == b'H': cursor = max(0, cursor - 1)
                    elif arr == b'P': cursor = min(len(conflicts_page) - 1, cursor + 1)
                elif k == b'\r':
                    if conflicts_page:
                        tid = conflicts_page[cursor]['transaction_id']
                        marked.remove(tid) if tid in marked else marked.add(tid)
                elif k.upper() in [b'S', b'C', b'N', b'I', b'Q']:
                    targets = [c for c in conflicts_page if c['transaction_id'] in marked]
                    return k.upper().decode('utf-8'), targets if targets else conflicts_page
                elif k == b'\x03': raise KeyboardInterrupt