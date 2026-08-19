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

    def limpar_tela(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def selecionar_modo_operacao(self):
        self.limpar_tela()
        
        logo = """
██████╗  █████╗ ████████╗ █████╗     ███╗   ███╗███████╗██████╗  ██████╗ ███████╗
██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗    ████╗ ████║██╔════╝██╔══██╗██╔════╝ ██╔════╝
██║  ██║███████║   ██║   ███████║    ██╔████╔██║█████╗  ██████╔╝██║  ███╗█████╗  
██║  ██║██╔══██║   ██║   ██╔══██║    ██║╚██╔╝██║██╔══╝  ██╔══██╗██║   ██║██╔══╝  
██████╔╝██║  ██║   ██║   ██║  ██║    ██║ ╚═╝ ██║███████╗██║  ██║╚██████╔╝███████╗
╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝    ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
        """
        self.console.print(Align.center(f"[bold bright_cyan]{logo}[/bold bright_cyan]"))
        self.console.print(Align.center(Panel("SELECIONE O MODO DE OPERAÇÃO - DATA MERGE v7.1 (HÍBRIDO MVC)", border_style="bright_cyan")))
        self.console.print("\n")
        self.console.print("   [bold bright_cyan]>[/bold bright_cyan] [bold bright_white][ 1 ][/bold bright_white] [bold bright_cyan]Operar com FORNECEDORES[/bold bright_cyan]")
        self.console.print("   [bold bright_magenta]>[/bold bright_magenta] [bold bright_white][ 2 ][/bold bright_white] [bold bright_magenta]Operar com PRODUTOS[/bold bright_magenta]")
        self.console.print("\n   [bold bright_white]Escolha (1 ou 2): [/bold bright_white]", end="")
        
        while True:
            tecla = msvcrt.getch()
            if tecla == b'1': return 1
            elif tecla == b'2': return 2
            elif tecla == b'\x03': raise KeyboardInterrupt

    def renderizar_hub_ui(self, pendentes_auto, len_sessao, tem_historico, modo_nome):
        self.limpar_tela()
        logo = """
██████╗  █████╗ ████████╗ █████╗     ███╗   ███╗███████╗██████╗  ██████╗ ███████╗
██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗    ████╗ ████║██╔════╝██╔══██╗██╔════╝ ██╔════╝
██║  ██║███████║   ██║   ███████║    ██╔████╔██║█████╗  ██████╔╝██║  ███╗█████╗  
██║  ██║██╔══██║   ██║   ██╔══██║    ██║╚██╔╝██║██╔══╝  ██╔══██╗██║   ██║██╔══╝  
██████╔╝██║  ██║   ██║   ██║  ██║    ██║ ╚═╝ ██║███████╗██║  ██║╚██████╔╝███████╗
╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝    ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
        """
        self.console.print(Align.center(f"[bold bright_cyan]{logo}[/bold bright_cyan]"))
        
        cor_modo = "bright_cyan" if modo_nome == "FORNECEDOR" else "bright_magenta"
        
        status_text = (
            f"  [white]📦 Substituições na Fila (Prontas para atualizar o Excel):[/white] [bold bright_green]{len_sessao}[/bold bright_green]  \n"
            f"  [white]🤖 Grupos de Conflito Pendentes:[/white] [bold bright_yellow]{pendentes_auto}[/bold bright_yellow]  "
        )
        self.console.print(Align.center(Panel(status_text, title=f"[bold bright_white] DATA MERGE v7.1 - Modo {modo_nome} [/bold bright_white]", border_style=cor_modo, padding=(1, 2))))
        
        self.console.print("\n")
        opcoes = [
            ("1", "🪄 Iniciar Assistente", "Inicia ou continua o tratamento automático de duplicados.", "bright_cyan"),
            ("2", "🎯 Forçar Substituição Manual", "Substitui um ID antigo por um oficial (De ➜ Para).", "bright_cyan"),
            ("3", "🔍 Pesquisar Registro (Raio-X)", "Consulta ONDE um registro está nas planilhas (Leitura).", "bright_yellow"),
            ("4", "👻 Caçador de Órfãos", "Auditoria de IDs lançados nas lojas que NÃO existem na base.", "bright_magenta"),
            ("5", "🗑️ Limpar Peso Morto", "Auditoria de itens cadastrados na base que NUNCA foram usados.", "bright_magenta"),
            ("6", "🔗 Sincronizador Referencial", "Cruza Contas a Pagar x Notas e corrige as quebras.", "bright_blue"),
            ("Z", "↩️ Desfazer Ação", "Desfaz a última substituição da sua sessão.", "bright_cyan"),
            ("E", "🚀 Atualizar Planilhas do Excel", "Aplica todas as substituições nas movimentações LOCAIS.", "bright_green"),
            ("Q", "🚪 Salvar e Sair", "Salva o progresso e encerra.", "bright_red")
        ]
        
        for tecla, titulo, desc, cor in opcoes:
            if not tem_historico and tecla == "Z":
                self.console.print(f"   [dim]> [ {tecla} ] {titulo}[/dim]\n           [dim]{desc} (Histórico Vazio)[/dim]\n")
            else:
                self.console.print(f"   [bold {cor}]>[/bold {cor}] [bold bright_white][ {tecla} ][/bold bright_white] [bold {cor}]{titulo}[/bold {cor}]\n           [dim white]{desc}[/dim white]\n")
                
        self.console.print("[dim]" + "─" * 85 + "[/dim]")
        self.console.print("   [bold bright_cyan]>[/bold bright_cyan] [blink]Aguardando comando...[/blink] ", end="")

    def menu_interativo_nativo(self, grupo, itens_pendentes, marcados, idx_grupo, total_grupos, total_migracoes, pode_desfazer):
        self.limpar_tela()
        cursor = 0

        def render_layout(pos, marc):
            progresso_txt = f"[bold bright_white]PROGRESSO:[/bold bright_white] Grupo {idx_grupo} de {total_grupos} | [bold bright_green]Substituições Salvas:[/bold bright_green] {total_migracoes}"
            panel_progresso = Panel(Align.center(progresso_txt), border_style="dim white")
            
            info_grupo = f"[bold bright_yellow]Motivo do Agrupamento:[/bold bright_yellow] {escape(grupo.motivo)}\n[bold bright_green]ID Oficial Sugerido:[/bold bright_green] {grupo.mestre.id} ({escape(grupo.mestre.nome)})"
            panel_info = Panel(info_grupo, title=f"[bold bright_cyan]GRUPO DE CONFLITO: {escape(grupo.nome)}[/bold bright_cyan]", border_style="bright_cyan")
            
            table = Table(show_header=True, header_style="bold bright_magenta", box=box.ROUNDED, show_lines=True)
            table.add_column("Sel", justify="center", vertical="middle")
            table.add_column("ID Antigo", style="bright_yellow", vertical="middle")
            table.add_column("Ocor.", justify="right", style="bright_green", vertical="middle")
            table.add_column("Nome do Registro", style="bright_white", vertical="middle")
            
            for i, f in enumerate(itens_pendentes):
                is_selected = f.id in marc
                is_cursor = i == pos
                
                sel_char = "[bold bright_green][ X ][/]" if is_selected else "[dim][   ][/]"
                cursor_char = "[bold bright_cyan]➜[/] " if is_cursor else "  "
                row_style = "bold bright_white" if is_cursor else "white"
                if is_selected and not is_cursor: row_style = "bright_green"
                
                table.add_row(f"{cursor_char}{sel_char}", f"[{row_style}]{f.id}[/]", f"[{row_style}]{f.movimentacoes}[/]", f"[{row_style}]{escape(f.nome)}[/]")
                
            item_focado = itens_pendentes[pos]
            if item_focado.movimentacoes > 0:
                detalhes_table = Table(show_header=True, header_style="dim bright_cyan", box=box.SIMPLE_HEAD, expand=True)
                detalhes_table.add_column("Loja", style="bright_white")
                detalhes_table.add_column("Aba", style="bright_cyan")
                detalhes_table.add_column("Coluna", style="bright_yellow")
                detalhes_table.add_column("Qtd", justify="right", style="bold bright_green")

                resumo_raiox = {}
                for loc, qtd in item_focado.movimentacoes_por_loja.items():
                    loja, aba, coluna = self._limpar_nome_loja(loc)
                    chave = (loja, aba, coluna)
                    resumo_raiox[chave] = resumo_raiox.get(chave, 0) + qtd

                for (loja, aba, col), qtd in sorted(resumo_raiox.items()):
                    detalhes_table.add_row(escape(loja), escape(aba), escape(col), str(qtd))
                
                panel_detalhes = Panel(detalhes_table, title=f"[bold bright_cyan]🔎 Raio-X do ID: {escape(item_focado.id)}[/]", border_style="bright_cyan")
            else:
                panel_detalhes = Panel("\n\n[dim white]Nenhuma ocorrência encontrada para este\nproduto nas abas permitidas.[/dim white]\n\n", title=f"[bold bright_cyan]🔎 Raio-X do ID: {escape(item_focado.id)}[/]", border_style="dim")

            layout_duplo = Table.grid(expand=True)
            layout_duplo.add_column(ratio=6)
            layout_duplo.add_column(ratio=4)
            layout_duplo.add_row(table, panel_detalhes)
            
            qtd = len(marc)
            alvo_txt = f"nos {qtd} marcados" if qtd > 0 else "em TODOS"
            
            atalhos = (
                f"[bold bright_white]ATALHOS DIRETOS (A ação será aplicada {alvo_txt}):[/bold bright_white]\n\n"
                f" [bold bright_cyan][S][/bold bright_cyan] Substituir selecionados pelo ID Oficial Sugerido\n"
                f" [bold bright_cyan][I][/bold bright_cyan] Informar ID / Pesquisar Manualmente (Escolher outro Oficial)\n"
                f" [bold bright_cyan][T][/bold bright_cyan] Trazer outro(s) registro(s) para resolver neste grupo\n"
                f" [bold bright_red][P][/bold bright_red] Pular / Manter Intacto\n\n"
                f" [bold bright_yellow][Z][/bold bright_yellow] Desfazer última substituição{'' if pode_desfazer else ' [dim](Indisponível - Vazio)[/dim]'}\n"
                f" [bold bright_yellow][V][/bold bright_yellow] Voltar para um Grupo Específico (Rollback){'' if pode_desfazer else ' [dim](Indisponível - Vazio)[/dim]'}\n"
                f" [bold bright_magenta][Q][/bold bright_magenta] Pausar Sessão e Voltar ao Hub"
            )
            panel_atalhos = Panel(atalhos, border_style="dim white")

            return Group(
                panel_progresso, panel_info,
                Text(" NAVEGAÇÃO: Setas (Cima/Baixo) | SELEÇÃO (Marcar): [ENTER]\n", style="dim"),
                layout_duplo,
                panel_atalhos
            )

        with Live(render_layout(cursor, marcados), console=self.console, auto_refresh=False) as live:
            while True:
                if cursor >= len(itens_pendentes):
                    cursor = max(0, len(itens_pendentes) - 1)
                    live.update(render_layout(cursor, marcados), refresh=True)

                tecla = msvcrt.getch()
                if tecla in (b'\xe0', b'\x00'):
                    seta = msvcrt.getch()
                    if seta == b'H': cursor = max(0, cursor - 1)
                    elif seta == b'P': cursor = min(len(itens_pendentes) - 1, cursor + 1)
                    live.update(render_layout(cursor, marcados), refresh=True)
                elif tecla == b'\r':
                    if itens_pendentes:
                        item_id = itens_pendentes[cursor].id
                        if item_id in marcados: marcados.remove(item_id)
                        else: marcados.add(item_id)
                        live.update(render_layout(cursor, marcados), refresh=True)
                elif tecla.upper() == b'S': return 'S'
                elif tecla.upper() == b'I': return 'I'
                elif tecla.upper() == b'T': return 'T'
                elif tecla.upper() == b'P': return 'P'
                elif tecla.upper() == b'Q': return 'Q'
                elif tecla.upper() == b'Z' and pode_desfazer: return 'Z'
                elif tecla.upper() == b'V' and pode_desfazer: return 'V'
                elif tecla == b'\x03': raise KeyboardInterrupt

    def menu_pesquisa_nativo(self, resultados, termo_busca, sessao_atual, ids_processados):
        self.limpar_tela()
        cursor = 0
        opcoes = resultados + ["EXTERNO"]

        def render_layout(pos):
            table = Table(show_header=True, header_style="bold bright_magenta", box=box.ROUNDED, show_lines=True)
            table.add_column("Sel", justify="center", vertical="middle")
            table.add_column("Status Atual", vertical="middle")
            table.add_column("ID", style="bright_yellow", vertical="middle")
            table.add_column("Nome do Registro", vertical="middle")
            table.add_column("Ocorrências", vertical="middle")

            for i, item in enumerate(opcoes):
                is_cursor = i == pos
                cursor_char = "[bold bright_cyan] ➜ [/bold bright_cyan]" if is_cursor else "   "
                row_style = "bold bright_white" if is_cursor else "white"
                
                if item == "EXTERNO":
                    table.add_row(cursor_char, "-", "-", f"[{row_style}]\\[ Usar '{escape(termo_busca)}' como um ID Externo / Não Cadastrado ][/]", "-")
                else:
                    status_tag = f"[{row_style}][dim white]INTACTO[/dim white][/]"
                    if item.id in sessao_atual: status_tag = f"[bold red]SUBSTITUÍDO p/ {sessao_atual[item.id]}[/bold red]"
                    elif item.id in ids_processados: status_tag = "[bold bright_yellow]PULADO[/bold bright_yellow]"
                    elif hasattr(item, 'movimentacoes_originais') and item.movimentacoes > item.movimentacoes_originais:
                        status_tag = f"[bold bright_green]HERDOU LINHAS[/bold bright_green]"
                    elif item.movimentacoes == 0: status_tag = "[dim red]ZERADO[/dim red]"

                    table.add_row(cursor_char, status_tag, f"[{row_style}]{item.id}[/]", f"[{row_style}]{escape(item.nome)}[/]", f"[{row_style}]{item.movimentacoes}[/]")

            return Group(
                Panel(f"[bold bright_cyan]PESQUISA DE ID OFICIAL:[/bold bright_cyan] [bright_white]'{escape(termo_busca)}'[/bright_white]", border_style="bright_cyan"),
                Text(" NAVEGAÇÃO: Setas (Cima/Baixo) | SELEÇÃO: [ENTER] | CANCELAR: [ESC]\n", style="dim"),
                table
            )

        with Live(render_layout(cursor), console=self.console, auto_refresh=False) as live:
            while True:
                tecla = msvcrt.getch()
                if tecla in (b'\xe0', b'\x00'):
                    seta = msvcrt.getch()
                    if seta == b'H': cursor = max(0, cursor - 1)
                    elif seta == b'P': cursor = min(len(opcoes) - 1, cursor + 1)
                    live.update(render_layout(cursor), refresh=True)
                elif tecla == b'\r': return opcoes[cursor]
                elif tecla == b'\x1b': return None
                elif tecla == b'\x03': raise KeyboardInterrupt

    def menu_pesquisa_multi(self, resultados, termo_busca, sessao_atual, ids_processados, pendentes_ids):
        self.limpar_tela()
        cursor = 0
        marcados = set()

        def render_layout(pos, marc):
            table = Table(show_header=True, header_style="bold bright_magenta", box=box.ROUNDED, show_lines=True)
            table.add_column("Sel", justify="center", vertical="middle")
            table.add_column("Status Atual", vertical="middle")
            table.add_column("ID", style="bright_yellow", vertical="middle")
            table.add_column("Nome do Registro", vertical="middle")
            table.add_column("Ocorrências", vertical="middle")

            for i, item in enumerate(resultados):
                is_cursor = i == pos
                is_selected = item.id in marc
                in_group = item.id in pendentes_ids
                
                cursor_char = "[bold bright_cyan] ➜ [/bold bright_cyan]" if is_cursor else "   "
                row_style = "bold bright_white" if is_cursor else "white"
                if is_selected and not is_cursor: row_style = "bright_green"
                
                sel_char = "[dim][   ][/]"
                if in_group: sel_char = "[dim bright_blue][ G ][/]"
                elif is_selected: sel_char = "[bold bright_green][ X ][/]"
                
                status_tag = f"[{row_style}][dim white]INTACTO[/dim white][/]"
                if item.id in sessao_atual: status_tag = f"[bold red]SUBSTITUÍDO p/ {sessao_atual[item.id]}[/bold red]"
                elif item.id in ids_processados: status_tag = "[bold bright_yellow]PULADO[/bold bright_yellow]"
                elif hasattr(item, 'movimentacoes_originais') and item.movimentacoes > item.movimentacoes_originais:
                    status_tag = f"[bold bright_green]HERDOU LINHAS[/bold bright_green]"
                elif item.movimentacoes == 0: status_tag = "[dim red]ZERADO[/dim red]"

                table.add_row(f"{cursor_char}{sel_char}", status_tag, f"[{row_style}]{item.id}[/]", f"[{row_style}]{escape(item.nome)}[/]", f"[{row_style}]{item.movimentacoes}[/]")

            return Group(
                Panel(f"[bold bright_cyan]PESQUISA MÚLTIPLA:[/bold bright_cyan] [bright_white]'{escape(termo_busca)}'[/bright_white]", border_style="bright_cyan"),
                Text(" NAVEGAÇÃO: Setas (Cima/Baixo) | MARCAR: [ENTER] | CONFIRMAR SELEÇÃO: [C] | CANCELAR: [ESC]\n", style="dim"),
                table,
                Text(f"\n Selecionados: {len(marc)} (Pressione C para confirmar)", style="bold bright_green")
            )

        with Live(render_layout(cursor, marcados), console=self.console, auto_refresh=False) as live:
            while True:
                tecla = msvcrt.getch()
                if tecla in (b'\xe0', b'\x00'):
                    seta = msvcrt.getch()
                    if seta == b'H': cursor = max(0, cursor - 1)
                    elif seta == b'P': cursor = min(len(resultados) - 1, cursor + 1)
                    live.update(render_layout(cursor, marcados), refresh=True)
                elif tecla == b'\r': 
                    item_id = resultados[cursor].id
                    if item_id not in pendentes_ids:
                        if item_id in marcados: marcados.remove(item_id)
                        else: marcados.add(item_id)
                    live.update(render_layout(cursor, marcados), refresh=True)
                elif tecla.upper() == b'C': return [r for r in resultados if r.id in marcados]
                elif tecla == b'\x1b': return []
                elif tecla == b'\x03': raise KeyboardInterrupt

    def exibir_confirmacao_migracao(self, alvos, dest_id, nome_dest, dest_forn, modo_nome):
        self.limpar_tela()
        self.console.print(Panel("[bold bright_cyan]REVISÃO DE IMPACTO (SUBSTITUIÇÃO DE IDs)[/bold bright_cyan]", border_style="bright_cyan"))
        
        t_origem = Table(title=f"\n[bold bright_red]IDs ANTIGOS ({modo_nome}) QUE SERÃO SUBSTITUÍDOS[/bold bright_red]", show_header=True, header_style="bold bright_red", box=box.ROUNDED, expand=True, show_lines=True)
        t_origem.add_column("ID Antigo", style="bright_yellow", vertical="middle")
        t_origem.add_column("Nome Descontinuado", style="bright_white", vertical="middle")
        t_origem.add_column("Linhas Afetadas", style="bold red", justify="center", vertical="middle")
        t_origem.add_column("Impacto Agrupado", style="white", vertical="middle")
        
        total_movido = 0
        resumo_lojas = {}
        
        for f in alvos:
            if f.id == dest_id: continue
            
            texto_loc = self._formatar_localizacao_agrupada(f.movimentacoes_por_loja)
            
            for loja_raw, qtd in f.movimentacoes_por_loja.items():
                loja, aba, coluna = self._limpar_nome_loja(loja_raw)
                resumo_lojas[loja] = resumo_lojas.get(loja, 0) + qtd
                
            t_origem.add_row(f.id, escape(f.nome), str(f.movimentacoes), texto_loc)
            total_movido += f.movimentacoes
            
        self.console.print(t_origem)
        
        qtd_atual = dest_forn.movimentacoes if dest_forn else 0
        qtd_final = qtd_atual + total_movido
        resumo_str_list = [f"[bold white]{qtd}[/bold white] em {loja}" for loja, qtd in resumo_lojas.items()]
        resumo_texto = ", ".join(resumo_str_list) if resumo_str_list else "Nenhuma linha alterada"
        
        dest_panel = (
            f"  [bold bright_white]NOVO ID (QUE ASSUMIRÁ AS LINHAS):[/bold bright_white] [bright_yellow]{dest_id}[/bright_yellow]\n"
            f"  [bold bright_white]NOME CORRETO:[/bold bright_white] {escape(nome_dest)}\n\n"
            f"  [dim]Linhas atuais com este ID:[/dim] {qtd_atual}\n"
            f"  [bold bright_green]LINHAS APÓS SUBSTITUIÇÃO:[/bold bright_green] [bold white]{qtd_final}[/bold white] [bold bright_green](+{total_movido} atualizadas)[/bold bright_green]\n\n"
            f"  [bold bright_magenta]RESUMO DA AÇÃO:[/bold bright_magenta] O novo ID será injetado em: {resumo_texto}."
        )
        self.console.print(Panel(dest_panel, title=f"[bold bright_green]REGISTRO DESTINO (ID OFICIAL DO {modo_nome})[/bold bright_green]", border_style="bright_green"))
        
        self.console.print("\n[bold bright_white] Pressione [ENTER] para Confirmar a Substituição ou [ESC] para Cancelar... [/bold bright_white]", end="")
        while True:
            t = msvcrt.getch()
            if t == b'\r': return True
            if t == b'\x1b': return False

    def desenhar_tela_raiox(self, alvo):
        titulo_box = f"[bold bright_yellow]🔍 RESULTADO DO RAIO-X[/bold bright_yellow]\n[bold white]ID:[/bold white] {alvo.id} | [bold white]NOME:[/bold white] {escape(alvo.nome)}"
        self.console.print(Panel(titulo_box, border_style="bright_yellow"))
        
        if alvo.movimentacoes > 0:
            t_raiox = Table(show_header=True, header_style="bold bright_yellow", box=box.ROUNDED, expand=True, show_lines=True)
            t_raiox.add_column("🏪 Loja / Arquivo", style="bright_white", vertical="middle")
            t_raiox.add_column("📑 Aba (Planilha)", style="bright_cyan", vertical="middle")
            t_raiox.add_column("🏷️ Coluna", style="bright_yellow", vertical="middle")
            t_raiox.add_column("📦 Quantidade", justify="right", style="bold bright_green", vertical="middle")
            
            resumo_raiox = {}
            for loc_raw, qtd in alvo.movimentacoes_por_loja.items():
                loja, aba, coluna = self._limpar_nome_loja(loc_raw)
                chave = (loja, aba, coluna)
                resumo_raiox[chave] = resumo_raiox.get(chave, 0) + qtd

            for (loja, aba, col), qtd in sorted(resumo_raiox.items()):
                t_raiox.add_row(escape(loja), escape(aba), escape(col), str(qtd))
                
            self.console.print(t_raiox)
            self.console.print(f"\n[dim white]Total: {alvo.movimentacoes} ocorrência(s) encontrada(s) no sistema.[/dim white]")
        else:
            self.console.print("\n[bold red]Este registro existe na sua base oficial, mas não foi encontrado nenhuma vez nas planilhas escaneadas.[/bold red]")
            
        self.console.print("\n[bold bright_white]Pressione qualquer tecla para voltar ao Menu Principal...[/bold bright_white]")
        msvcrt.getch()

    def paginar_orfaos(self, orfaos_ordenados, modo_nome):
        total_geral_linhas = sum(sum(locs.values()) for _, locs in orfaos_ordenados)
        tamanho_pagina = 10
        total_paginas = (len(orfaos_ordenados) + tamanho_pagina - 1) // tamanho_pagina
        pagina_atual = 0
        
        while True:
            self.limpar_tela()
            self.console.print(Panel(f"[bold bright_magenta]👻 CAÇADOR DE ÓRFÃOS ({modo_nome}S FANTASMAS)[/bold bright_magenta]", border_style="bright_magenta"))
            
            t_orfaos = Table(show_header=True, header_style="bold bright_magenta", box=box.ROUNDED, expand=True, show_lines=True)
            t_orfaos.add_column("ID Fantasma", style="bold bright_yellow", vertical="middle")
            t_orfaos.add_column("Qtd", justify="center", style="bold bright_red", vertical="middle")
            t_orfaos.add_column("📍 Onde encontrar (Agrupado por Loja)", style="white", vertical="middle")
            
            inicio = pagina_atual * tamanho_pagina
            fim = inicio + tamanho_pagina
            
            for orf_id, locs in orfaos_ordenados[inicio:fim]:
                total_loc = sum(locs.values())
                texto_loc = self._formatar_localizacao_agrupada(locs)
                t_orfaos.add_row(escape(str(orf_id)), str(total_loc), texto_loc)
                
            self.console.print(t_orfaos)
            
            self.console.print(f"\n[bold bright_red]Resumo Geral:[/bold bright_red] {len(orfaos_ordenados)} IDs não cadastrados no total (Impactando {total_geral_linhas} linhas).")
            self.console.print(f"[bold bright_cyan]Exibindo grupo {pagina_atual + 1} de {total_paginas}[/bold bright_cyan]\n")
            
            opcoes_rodape = []
            if pagina_atual < total_paginas - 1:
                opcoes_rodape.append("[bold bright_white][N][/bold bright_white] Próximo Grupo")
            if pagina_atual > 0:
                opcoes_rodape.append("[bold bright_white][A][/bold bright_white] Grupo Anterior")
            opcoes_rodape.append("[bold bright_white][E][/bold bright_white] Exportar Relatório .txt")
            opcoes_rodape.append("[bold bright_white][Q][/bold bright_white] Voltar ao Menu")
            
            self.console.print(" | ".join(opcoes_rodape))
            
            t_acao = msvcrt.getch().upper()
            
            if (t_acao == b'N' or t_acao == b'P') and pagina_atual < total_paginas - 1:
                pagina_atual += 1
            elif (t_acao == b'A' or t_acao == b'V') and pagina_atual > 0:
                pagina_atual -= 1
            elif t_acao == b'E':
                with open("RELATORIO_ORFAOS.txt", "w", encoding="utf-8") as f_out:
                    f_out.write(f"=== RELATORIO DE {modo_nome}S ORFAOS (FANTASMAS) ===\n")
                    f_out.write("Estes IDs foram lancados nas lojas, mas NAO existem na base oficial:\n\n")
                    for orf_id, locs in orfaos_ordenados:
                        f_out.write(f"ID FANTASMA: {orf_id} (Aparece {sum(locs.values())} vezes)\n")
                        for loc_raw, qtd in locs.items():
                            loja, aba, coluna = self._limpar_nome_loja(loc_raw)
                            f_out.write(f"  -> Loja: {loja} | Aba: {aba} | Coluna: {coluna} | Quantidade: {qtd}\n")
                        f_out.write("-" * 50 + "\n")
                utils_console.sucesso("\nRelatório exportado com sucesso: RELATORIO_ORFAOS.txt")
                time.sleep(2)
            elif t_acao == b'Q' or t_acao == b'\x1b':
                break

    def paginar_inativos(self, inativos, modo_nome):
        tamanho_pagina = 10
        total_paginas = (len(inativos) + tamanho_pagina - 1) // tamanho_pagina
        pagina_atual = 0
        
        while True:
            self.limpar_tela()
            self.console.print(Panel(f"[bold bright_magenta]🗑️ LIMPEZA DE PESO MORTO ({modo_nome}S INATIVOS)[/bold bright_magenta]", border_style="bright_magenta"))
            
            t_inativos = Table(show_header=True, header_style="bold bright_magenta", box=box.ROUNDED, expand=True, show_lines=True)
            t_inativos.add_column("ID Oficial", style="bright_yellow", vertical="middle")
            t_inativos.add_column("Nome do Registro", style="bright_white", vertical="middle")
            
            inicio = pagina_atual * tamanho_pagina
            fim = inicio + tamanho_pagina
            
            for inativo in inativos[inicio:fim]:
                t_inativos.add_row(escape(inativo.id), escape(inativo.nome))
                
            self.console.print(t_inativos)
            
            self.console.print(f"\n[bold bright_yellow]Resumo Geral:[/bold bright_yellow] Foram encontrados {len(inativos)} registros com ZERO compras no sistema.")
            self.console.print(f"[bold bright_cyan]Exibindo grupo {pagina_atual + 1} de {total_paginas}[/bold bright_cyan]\n")
            
            opcoes_rodape = []
            if pagina_atual < total_paginas - 1:
                opcoes_rodape.append("[bold bright_white][N][/bold bright_white] Próximo Grupo")
            if pagina_atual > 0:
                opcoes_rodape.append("[bold bright_white][A][/bold bright_white] Grupo Anterior")
            opcoes_rodape.append("[bold bright_white][E][/bold bright_white] Exportar Relatório .txt")
            opcoes_rodape.append("[bold bright_white][Q][/bold bright_white] Voltar ao Menu")
            
            self.console.print(" | ".join(opcoes_rodape))
            
            t_acao = msvcrt.getch().upper()
            
            if (t_acao == b'N' or t_acao == b'P') and pagina_atual < total_paginas - 1:
                pagina_atual += 1
            elif (t_acao == b'A' or t_acao == b'V') and pagina_atual > 0:
                pagina_atual -= 1
            elif t_acao == b'E':
                with open("RELATORIO_PESO_MORTO.txt", "w", encoding="utf-8") as f_out:
                    f_out.write(f"=== RELATORIO DE {modo_nome}S INATIVOS (PESO MORTO) ===\n")
                    f_out.write("Estes registros existem na base oficial, mas NUNCA foram usados em nenhuma loja:\n\n")
                    for inativo in inativos:
                        f_out.write(f"ID: {inativo.id} | Nome: {inativo.nome}\n")
                utils_console.sucesso("\nRelatório exportado com sucesso: RELATORIO_PESO_MORTO.txt")
                time.sleep(2)
            elif t_acao == b'Q' or t_acao == b'\x1b':
                break

    def desenhar_tabela_cruzada(self, conflito):
        t_cruzamento = Table(show_header=True, header_style="bold white", box=box.ROUNDED, expand=True)
        t_cruzamento.add_column("Onde", style="bright_cyan")
        t_cruzamento.add_column("📍 Localização Exata", style="white")
        t_cruzamento.add_column("Status do Fornecedor", justify="center")
        t_cruzamento.add_column("ID Lançado", style="bright_yellow")
        
        def cor_st(st):
            if st == "OFICIAL": return "[bold bright_green]✅ OFICIAL[/]"
            if st == "VAZIO": return "[dim white]🕳️ VAZIO[/]"
            return "[bold red]👻 FANTASMA[/]"
            
        loc_conta = f"{os.path.basename(conflito['conta']['arquivo']).replace('.xlsx', '')} ➜ {escape(conflito['conta']['aba'])} (Linha {conflito['conta']['row']})"
        loc_nota = f"{os.path.basename(conflito['nota']['arquivo']).replace('.xlsx', '')} ➜ {escape(conflito['nota']['aba'])} (Linha {conflito['nota']['row']})"
            
        t_cruzamento.add_row("Contas a Pagar", loc_conta, cor_st(conflito['st_c']), escape(conflito['conta']['val'] or "---"))
        t_cruzamento.add_row("Nota de Compra", loc_nota, cor_st(conflito['st_n']), escape(conflito['nota']['val'] or "---"))
        
        self.console.print(t_cruzamento)

    def paginar_conflitos(self, conflitos, pagina_atual):
        tamanho_pagina = 10
        total_paginas = max(1, (len(conflitos) + tamanho_pagina - 1) // tamanho_pagina)
        
        self.limpar_tela()
        self.console.print(Panel("[bold bright_blue]🔗 CAÇADOR DE QUEBRAS REFERENCIAIS (Contas x Notas)[/bold bright_blue]", border_style="bright_blue"))
        
        t_conflitos = Table(show_header=True, header_style="bold bright_blue", box=box.ROUNDED, expand=True, show_lines=True)
        t_conflitos.add_column("Loja (Arquivo)", style="bright_cyan", vertical="middle")
        t_conflitos.add_column("Nº Nota", justify="center", style="bold bright_yellow", vertical="middle")
        t_conflitos.add_column("ID Contas a Pagar", style="white", vertical="middle")
        t_conflitos.add_column("ID Nota Compra", style="white", vertical="middle")
        t_conflitos.add_column("Ação Sugerida", style="bold bright_green", vertical="middle")
        
        inicio = pagina_atual * tamanho_pagina
        fim = inicio + tamanho_pagina
        conflitos_pagina = conflitos[inicio:fim]
        
        def formatar_status(val, st):
            v = escape(val) if val else "---"
            if st == "OFICIAL": return f"{v} [bold bright_green](OFICIAL)[/]"
            if st == "VAZIO": return f"{v} [dim white](VAZIO)[/]"
            return f"{v} [bold red](FANTASMA)[/]"
            
        for c in conflitos_pagina:
            loja = self._limpar_nome_loja(c['conta']['arquivo'])[0]
            n_nota = str(c['id_nota'])
            st_c = formatar_status(c['conta']['val'], c['st_c'])
            st_n = formatar_status(c['nota']['val'], c['st_n'])
            sugestao = f"Espelhar ID: {c['sugestao_id']}" if c['sugestao_id'] else "[bold red]Requer Manual[/]"
            
            t_conflitos.add_row(escape(loja), escape(n_nota), st_c, st_n, sugestao)
            
        self.console.print(t_conflitos)
        
        self.console.print(f"\n[bold bright_yellow]Resumo Geral:[/bold bright_yellow] Foram encontradas {len(conflitos)} notas com quebra de integridade.")
        self.console.print(f"[bold bright_cyan]Exibindo grupo {pagina_atual + 1} de {total_paginas}[/bold bright_cyan]\n")
        
        opcoes_rodape = []
        if pagina_atual < total_paginas - 1:
            opcoes_rodape.append("[bold bright_white][N][/bold bright_white] Próximo Grupo")
        if pagina_atual > 0:
            opcoes_rodape.append("[bold bright_white][A][/bold bright_white] Grupo Anterior")
        
        opcoes_rodape.append("[bold bright_green][R][/bold bright_green] Resolver as notas desta Tela")
        opcoes_rodape.append("[bold bright_white][E][/bold bright_white] Exportar Relatório .txt")
        opcoes_rodape.append("[bold bright_white][Q][/bold bright_white] Voltar ao Menu")
        
        self.console.print(" | ".join(opcoes_rodape))
        
        while True:
            t_acao = msvcrt.getch().upper()
            if t_acao in [b'N', b'P'] and pagina_atual < total_paginas - 1: return 'PROXIMO'
            elif t_acao in [b'A', b'V'] and pagina_atual > 0: return 'ANTERIOR'
            elif t_acao == b'R': return 'RESOLVER'
            elif t_acao == b'E': return 'EXPORTAR'
            elif t_acao in [b'Q', b'\x1b']: return 'SAIR'

    def exibir_erro_critico(self, traceback_msg):
        self.limpar_tela()
        self.console.print(Panel(f"[bold bright_red]ERRO CRÍTICO NA INICIALIZAÇÃO[/bold bright_red]", border_style="red"))
        self.console.print(f"[white]Verifique se a internet está conectada, se o link no config.py está correto ou se o credentials.json está na pasta.[/white]\n\n[dim]Detalhe do erro:\n{traceback_msg}[/dim]")

    # ==========================================
    # HELPERS INTERNOS DE TEXTO
    # ==========================================
    def _limpar_nome_loja(self, nome_bruto):
        partes = nome_bruto.split(" | ")
        if len(partes) == 3:
            caminho, aba, coluna = partes
            loja = os.path.basename(caminho).replace("Movimentações - ", "").replace("Contas a Pagar - ", "").strip()
            return loja, aba, coluna
        loja = os.path.basename(nome_bruto).replace(".xlsx", "").strip()
        return loja, "-", "-"

    def _formatar_localizacao_agrupada(self, movimentacoes_dict):
        if not movimentacoes_dict: return "-"
        
        resumo = {}
        for loc_raw, qtd in movimentacoes_dict.items():
            loja, aba, coluna = self._limpar_nome_loja(loc_raw)
            if loja not in resumo: resumo[loja] = {'total': 0, 'abas': {}, 'colunas': {}}
            resumo[loja]['abas'][aba] = resumo[loja]['abas'].get(aba, 0) + qtd
            col_nome = coluna if coluna and coluna != "-" else "Desconhecida"
            resumo[loja]['colunas'][col_nome] = resumo[loja]['colunas'].get(col_nome, 0) + qtd
            resumo[loja]['total'] += qtd
            
        blocos = []
        lojas_ordenadas = sorted(resumo.items(), key=lambda x: x[1]['total'], reverse=True)
        
        for loja, dados in lojas_ordenadas:
            linhas_loja = []
            linhas_loja.append(f"[bold bright_cyan]Loja:[/] [white]{escape(loja)}[/]")
            linhas_loja.append(f"[bold bright_green]Quantidade total:[/] [white]{dados['total']}[/]")
            abas_str = ", ".join([f"{escape(aba)} ({qtd})" for aba, qtd in dados['abas'].items()])
            linhas_loja.append(f"[bold bright_magenta]Abas:[/] [white]{abas_str}[/]")
            colunas_str = ", ".join([f"{escape(col)} ({qtd})" for col, qtd in dados['colunas'].items()])
            linhas_loja.append(f"[bold bright_yellow]Colunas:[/] [white]{colunas_str}[/]")
            blocos.append("\n".join(linhas_loja))
                
        return "\n\n".join(blocos)
    
    def menu_resolucao_lote(self, conflitos_pagina, total_restantes):
        self.limpar_tela()
        cursor = 0
        marcados = set()

        def render_layout(pos, marc):
            panel_info = Panel(f"[bold bright_blue]🔗 MODO DE RESOLUÇÃO EM LOTE[/bold bright_blue]\nFaltam [bold bright_yellow]{total_restantes}[/bold bright_yellow] notas pendentes. As resolvidas puxam as próximas da fila automaticamente.", border_style="bright_blue")
            
            table = Table(show_header=True, header_style="bold bright_magenta", box=box.ROUNDED, show_lines=True)
            table.add_column("Sel", justify="center", vertical="middle")
            table.add_column("Nº Nota", style="bold bright_yellow", justify="center")
            table.add_column("Contas a Pagar", style="white")
            table.add_column("Notas de Compra", style="white")
            table.add_column("Sugestão Automática", style="bold bright_green")
            
            for i, c in enumerate(conflitos_pagina):
                is_selected = c['id_nota'] in marc
                is_cursor = i == pos
                
                sel_char = "[bold bright_green][ X ][/]" if is_selected else "[dim][   ][/]"
                cursor_char = "[bold bright_cyan]➜[/] " if is_cursor else "  "
                row_style = "bold bright_white" if is_cursor else "white"
                if is_selected and not is_cursor: row_style = "bright_green"
                
                st_c_format = f"{escape(c['conta']['val'] or 'VAZIO')} ({c['st_c']})"
                st_n_format = f"{escape(c['nota']['val'] or 'VAZIO')} ({c['st_n']})"
                sugestao = escape(c['sugestao_id']) if c['sugestao_id'] else "Manual"
                
                table.add_row(f"{cursor_char}{sel_char}", f"[{row_style}]{c['id_nota']}[/]", f"[{row_style}]{st_c_format}[/]", f"[{row_style}]{st_n_format}[/]", f"[{row_style}]{sugestao}[/]")
                
            qtd = len(marc)
            alvo_txt = f"nas {qtd} notas marcadas" if qtd > 0 else "em TODAS da tela"
            
            atalhos = (
                f"[bold bright_white]ATALHOS (Aplicará {alvo_txt}):[/bold bright_white]\n\n"
                f" [bold bright_green][S][/bold bright_green] Aplicar a Sugestão Automática (onde houver)\n"
                f" [bold bright_cyan][C][/bold bright_cyan] Forçar IDs usando o lado do [bold]Contas a Pagar[/bold]\n"
                f" [bold bright_cyan][N][/bold bright_cyan] Forçar IDs usando o lado das [bold]Notas de Compra[/bold]\n"
                f" [bold bright_magenta][I][/bold bright_magenta] Pesquisar e forçar um ID externo/manual para todas\n\n"
                f" [bold red][Q][/bold red] Voltar para a Visão Macro"
            )
            
            return Group(
                panel_info,
                Text(" NAVEGAÇÃO: Setas (Cima/Baixo) | SELEÇÃO (Marcar): [ENTER]\n", style="dim"),
                table,
                Panel(atalhos, border_style="dim white")
            )

        with Live(render_layout(cursor, marcados), console=self.console, auto_refresh=False) as live:
            while True:
                if cursor >= len(conflitos_pagina):
                    cursor = max(0, len(conflitos_pagina) - 1)
                    live.update(render_layout(cursor, marcados), refresh=True)

                tecla = msvcrt.getch()
                if tecla in (b'\xe0', b'\x00'):
                    seta = msvcrt.getch()
                    if seta == b'H': cursor = max(0, cursor - 1)
                    elif seta == b'P': cursor = min(len(conflitos_pagina) - 1, cursor + 1)
                    live.update(render_layout(cursor, marcados), refresh=True)
                elif tecla == b'\r':
                    if conflitos_pagina:
                        item_id = conflitos_pagina[cursor]['id_nota']
                        if item_id in marcados: marcados.remove(item_id)
                        else: marcados.add(item_id)
                        live.update(render_layout(cursor, marcados), refresh=True)
                elif tecla.upper() in [b'S', b'C', b'N', b'I', b'Q']:
                    alvos = [c for c in conflitos_pagina if c['id_nota'] in marcados] if marcados else conflitos_pagina.copy()
                    return tecla.upper().decode('utf-8'), alvos
                elif tecla == b'\x03': raise KeyboardInterrupt