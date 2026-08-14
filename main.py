import os
import sys
import msvcrt
import json
import time
import warnings

# ==========================================
# IMPORTAÇÕES DA NOVA INTERFACE (RICH)
# ==========================================
from rich.console import Console, Group
from rich.panel import Panel
from rich.align import Align
from rich.table import Table
from rich import box
from rich.markup import escape
from rich.live import Live
from rich.text import Text

from services.excel_service import ExcelService
from services.duplicate_service import DuplicateService
from services.report_service import ReportService
from services.migration_service import MigrationService
from utils import console as utils_console

# Inicializa o motor visual avançado
ui = Console()
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

ARQUIVO_BACKUP = "backup_sessao.json"

def limpar_tela_hard():
    """ Marreta do Sistema Operacional para aniquilar fantasmas do buffer do terminal """
    os.system('cls' if os.name == 'nt' else 'clear')

# =========================================================================
# LÓGICA DE ESTADO (TEMPO REAL) E PERSISTÊNCIA
# =========================================================================

def salvar_progresso(sessao, historico):
    historico_serializado = []
    for acao in historico:
        historico_serializado.append({
            'tipo': acao['tipo'],
            'grupo_idx': acao['grupo_idx'],
            'alvos_ids': [a['obj'].id for a in acao['alvos']],
            'dest_fornecedor_id': acao['dest_fornecedor'].id if acao.get('dest_fornecedor') else None
        })
    dados = {
        "sessao_atual": sessao,
        "historico": historico_serializado
    }
    with open(ARQUIVO_BACKUP, "w", encoding="utf-8") as out:
        json.dump(dados, out, ensure_ascii=False, indent=4)

def aplicar_migracao_em_lote(alvos, dest_id, dest_forn, migration_service, sessao_atual, ids_processados, historico_acoes, tipo, grupo_idx):
    alvos_data = []
    for f in alvos:
        if f.id == dest_id: continue
        
        alvos_data.append({
            'obj': f,
            'movs': f.movimentacoes,
            'lojas': f.movimentacoes_por_loja.copy()
        })
        
        migration_service.criar_migracao_individual(f, dest_id)
        sessao_atual[f.id] = dest_id
        ids_processados.add(f.id)
        
        if dest_forn:
            dest_forn.movimentacoes += f.movimentacoes
            for loja, qtd in f.movimentacoes_por_loja.items():
                dest_forn.movimentacoes_por_loja[loja] = dest_forn.movimentacoes_por_loja.get(loja, 0) + qtd
                
        f.movimentacoes = 0
        f.movimentacoes_por_loja = {}

    if alvos_data:
        historico_acoes.append({
            'tipo': tipo,
            'grupo_idx': grupo_idx,
            'alvos': alvos_data,
            'dest_fornecedor': dest_forn
        })

def aplicar_pulo_em_lote(alvos, ids_processados, historico_acoes, grupo_idx):
    alvos_data = []
    for f in alvos:
        alvos_data.append({'obj': f})
        ids_processados.add(f.id)
    
    if alvos_data:
        historico_acoes.append({
            'tipo': 'P',
            'grupo_idx': grupo_idx,
            'alvos': alvos_data,
            'dest_fornecedor': None
        })

def reverter_acao(u_acao, sessao_atual, ids_processados, migration_service):
    dest_f = u_acao['dest_fornecedor']
    
    if u_acao['tipo'] in ['S', 'I', 'M']:
        for alvo_data in u_acao['alvos']:
            f = alvo_data['obj']
            t_movs = alvo_data['movs']
            t_lojas = alvo_data['lojas']
            
            migration_service.remover_migracao_individual(f.id)
            if f.id in sessao_atual: del sessao_atual[f.id]
            ids_processados.discard(f.id)
            
            if dest_f and f.id != dest_f.id: 
                dest_f.movimentacoes -= t_movs
                for loja, qtd in t_lojas.items():
                    dest_f.movimentacoes_por_loja[loja] -= qtd
                    if dest_f.movimentacoes_por_loja[loja] <= 0:
                        del dest_f.movimentacoes_por_loja[loja]
                        
            f.movimentacoes = t_movs
            f.movimentacoes_por_loja = t_lojas.copy()
            
    elif u_acao['tipo'] == 'P':
        for alvo_data in u_acao['alvos']: 
            ids_processados.discard(alvo_data['obj'].id)

def atualizar_pendencias_grupos(grupos_duplicados, ids_processados):
    for grupo in grupos_duplicados:
        grupo.itens_pendentes = [f for f in grupo.duplicados if f.id not in ids_processados]

def limpar_nome_loja(nome_arquivo):
    return nome_arquivo.replace("Movimentações - ", "").replace("Contas a Pagar - ", "").replace(".xlsx", "").strip()

# =========================================================================
# MENUS VISUAIS "LIVE" (AGORA COM SEMÂNTICA CORRETA)
# =========================================================================

def exibir_confirmacao_migracao(alvos, dest_id, nome_dest, dest_forn=None):
    limpar_tela_hard()
    ui.print(Panel("[bold bright_cyan]REVISÃO DE IMPACTO (SUBSTITUIÇÃO DE IDs)[/bold bright_cyan]", border_style="bright_cyan"))
    
    t_origem = Table(title="\n[bold bright_red]IDs ANTIGOS QUE SERÃO SUBSTITUÍDOS NO EXCEL[/bold bright_red]", show_header=True, header_style="bold bright_red", box=box.SIMPLE)
    t_origem.add_column("ID Antigo", style="bright_yellow")
    t_origem.add_column("Nome Descontinuado", style="bright_white")
    t_origem.add_column("Linhas Afetadas", style="bold red", justify="center")
    t_origem.add_column("Impacto por Arquivo (Loja)", style="dim white")
    
    total_movido = 0
    resumo_lojas = {}
    
    for f in alvos:
        if f.id == dest_id: continue
        detalhes = []
        for loja, qtd in f.movimentacoes_por_loja.items():
            l_limpa = limpar_nome_loja(loja)
            detalhes.append(f"{qtd} ocor. em {l_limpa}")
            resumo_lojas[l_limpa] = resumo_lojas.get(l_limpa, 0) + qtd
            
        detalhe_str = ", ".join(detalhes) if detalhes else "-"
        t_origem.add_row(f.id, escape(f.nome), str(f.movimentacoes), escape(detalhe_str))
        total_movido += f.movimentacoes
        
    ui.print(t_origem)
    
    qtd_atual = dest_forn.movimentacoes if dest_forn else 0
    qtd_final = qtd_atual + total_movido
    
    resumo_str_list = [f"[bold white]{qtd}[/bold white] ocorrência(s) no arq. de {loja}" for loja, qtd in resumo_lojas.items()]
    resumo_texto = ", ".join(resumo_str_list) if resumo_str_list else "Nenhuma linha alterada"
    
    dest_panel = (
        f"  [bold bright_white]NOVO ID (QUE ASSUMIRÁ AS LINHAS):[/bold bright_white] [bright_yellow]{dest_id}[/bright_yellow]\n"
        f"  [bold bright_white]NOME CORRETO:[/bold bright_white] {escape(nome_dest)}\n\n"
        f"  [dim]Linhas atuais com este ID:[/dim] {qtd_atual}\n"
        f"  [bold bright_green]LINHAS APÓS SUBSTITUIÇÃO:[/bold bright_green] [bold white]{qtd_final}[/bold white] [bold bright_green](+{total_movido} atualizadas)[/bold bright_green]\n\n"
        f"  [bold bright_magenta]RESUMO DA AÇÃO:[/bold bright_magenta] O novo ID será injetado em {resumo_texto}."
    )
    ui.print(Panel(dest_panel, title="[bold bright_green]FORNECEDOR DESTINO (ID OFICIAL)[/bold bright_green]", border_style="bright_green"))
    
    ui.print("\n[bold bright_white] Pressione [ENTER] para Confirmar a Substituição ou [ESC] para Cancelar... [/bold bright_white]", end="")
    while True:
        t = msvcrt.getch()
        if t == b'\r': return True
        if t == b'\x1b': return False

def menu_pesquisa_nativo(resultados, termo_busca, sessao_atual, ids_processados):
    limpar_tela_hard()
    cursor = 0
    opcoes = resultados + ["EXTERNO"]

    def render_layout(pos):
        table = Table(show_header=True, header_style="bold bright_magenta", box=box.SIMPLE)
        table.add_column("Sel", justify="center")
        table.add_column("Status Atual")
        table.add_column("ID", style="bright_yellow")
        table.add_column("Fornecedor")
        table.add_column("Ocorrências")

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

    with Live(render_layout(cursor), console=ui, auto_refresh=False) as live:
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

def menu_pesquisa_multi(resultados, termo_busca, sessao_atual, ids_processados, pendentes_ids):
    limpar_tela_hard()
    cursor = 0
    marcados = set()

    def render_layout(pos, marc):
        table = Table(show_header=True, header_style="bold bright_magenta", box=box.SIMPLE)
        table.add_column("Sel", justify="center")
        table.add_column("Status Atual")
        table.add_column("ID", style="bright_yellow")
        table.add_column("Fornecedor")
        table.add_column("Ocorrências")

        for i, item in enumerate(resultados):
            is_cursor = i == pos
            is_selected = item.id in marc
            in_group = item.id in pendentes_ids
            
            cursor_char = "[bold bright_cyan] ➜ [/bold bright_cyan]" if is_cursor else "   "
            row_style = "bold bright_white" if is_cursor else "white"
            if is_selected and not is_cursor: 
                row_style = "bright_green"
            
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

    with Live(render_layout(cursor, marcados), console=ui, auto_refresh=False) as live:
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

def menu_interativo_nativo(grupo, itens_pendentes, marcados, idx_grupo, total_grupos, total_migracoes, pode_desfazer):
    limpar_tela_hard()
    cursor = 0

    def render_layout(pos, marc):
        progresso_txt = f"[bold bright_white]PROGRESSO:[/bold bright_white] Grupo {idx_grupo} de {total_grupos} | [bold bright_green]Substituições Salvas:[/bold bright_green] {total_migracoes}"
        panel_progresso = Panel(Align.center(progresso_txt), border_style="dim white")
        
        info_grupo = f"[bold bright_yellow]Motivo do Agrupamento:[/bold bright_yellow] {escape(grupo.motivo)}\n[bold bright_green]ID Oficial Sugerido:[/bold bright_green] {grupo.mestre.id} ({escape(grupo.mestre.nome)})"
        panel_info = Panel(info_grupo, title=f"[bold bright_cyan]GRUPO DE CONFLITO: {escape(grupo.nome)}[/bold bright_cyan]", border_style="bright_cyan")
        
        table = Table(show_header=True, header_style="bold bright_magenta", box=box.SIMPLE)
        table.add_column("Sel", justify="center")
        table.add_column("ID Antigo", style="bright_yellow")
        table.add_column("Ocorrências", justify="right", style="bright_green")
        table.add_column("Fornecedor", style="bright_white")
        table.add_column("Localização no Arquivo (Lojas)", style="dim white")
        
        for i, f in enumerate(itens_pendentes):
            is_selected = f.id in marc
            is_cursor = i == pos
            
            sel_char = "[bold bright_green][ X ][/]" if is_selected else "[dim][   ][/]"
            cursor_char = "[bold bright_cyan]➜[/] " if is_cursor else "  "
            
            row_style = "bold bright_white" if is_cursor else "white"
            if is_selected and not is_cursor: 
                row_style = "bright_green"
            
            detalhes_loja = []
            for loja, qtd in f.movimentacoes_por_loja.items():
                detalhes_loja.append(f"{limpar_nome_loja(loja)}: {qtd}")
                
            detalhe_str = " | ".join(detalhes_loja)
            if f.movimentacoes == 0 and not detalhe_str: detalhe_str = "ZERADO"
            
            table.add_row(
                f"{cursor_char}{sel_char}",
                f"[{row_style}]{f.id}[/]",
                f"[{row_style}]{f.movimentacoes}[/]",
                f"[{row_style}]{escape(f.nome)}[/]",
                f"[{row_style}]{escape(detalhe_str)}[/]"
            )
            
        qtd = len(marc)
        alvo_txt = f"nos {qtd} marcados" if qtd > 0 else "em TODOS"
        
        atalhos = (
            f"[bold bright_white]ATALHOS DIRETOS (A ação será aplicada {alvo_txt}):[/bold bright_white]\n\n"
            f" [bold bright_cyan][S][/bold bright_cyan] Substituir selecionados pelo ID Oficial Sugerido\n"
            f" [bold bright_cyan][I][/bold bright_cyan] Informar ID / Pesquisar Manualmente (Escolher outro Oficial)\n"
            f" [bold bright_cyan][T][/bold bright_cyan] Trazer outro(s) Fornecedor(es) para resolver neste grupo\n"
            f" [bold bright_red][P][/bold bright_red] Pular / Manter Intacto\n\n"
            f" [bold bright_yellow][Z][/bold bright_yellow] Desfazer última substituição{'' if pode_desfazer else ' [dim](Indisponível - Vazio)[/dim]'}\n"
            f" [bold bright_yellow][V][/bold bright_yellow] Voltar para um Grupo Específico (Rollback){'' if pode_desfazer else ' [dim](Indisponível - Vazio)[/dim]'}\n"
            f" [bold bright_magenta][Q][/bold bright_magenta] Pausar Sessão e Voltar ao Hub"
        )
        panel_atalhos = Panel(atalhos, border_style="dim white")

        return Group(
            panel_progresso,
            panel_info,
            Text(" NAVEGAÇÃO: Setas (Cima/Baixo) | SELEÇÃO (Marcar): [ENTER]\n", style="dim"),
            table,
            panel_atalhos
        )

    with Live(render_layout(cursor, marcados), console=ui, auto_refresh=False) as live:
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

def renderizar_hub_ui(pendentes_auto, len_sessao, historico_acoes):
    limpar_tela_hard()
    logo = """
██████╗  █████╗ ████████╗ █████╗     ███╗   ███╗███████╗██████╗  ██████╗ ███████╗
██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗    ████╗ ████║██╔════╝██╔══██╗██╔════╝ ██╔════╝
██║  ██║███████║   ██║   ███████║    ██╔████╔██║█████╗  ██████╔╝██║  ███╗█████╗  
██║  ██║██╔══██║   ██║   ██╔══██║    ██║╚██╔╝██║██╔══╝  ██╔══██╗██║   ██║██╔══╝  
██████╔╝██║  ██║   ██║   ██║  ██║    ██║ ╚═╝ ██║███████╗██║  ██║╚██████╔╝███████╗
╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝    ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
    """
    ui.print(Align.center(f"[bold bright_cyan]{logo}[/bold bright_cyan]"))
    
    status_text = (
        f"  [white]📦 Substituições de IDs na Fila (Prontas para atualizar o Excel):[/white] [bold bright_green]{len_sessao}[/bold bright_green]  \n"
        f"  [white]🤖 Grupos de Conflito Pendentes:[/white] [bold bright_yellow]{pendentes_auto}[/bold bright_yellow]  "
    )
    ui.print(Align.center(Panel(status_text, title="[bold bright_white] TUI Engine v5.5 (Find & Replace Edition) [/bold bright_white]", border_style="bright_cyan", padding=(1, 2))))
    
    ui.print("\n")
    opcoes = [
        ("1", "🪄 Iniciar Assistente", "Inicia ou continua o tratamento automático de duplicados.", "bright_cyan"),
        ("2", "🎯 Forçar Substituição Manual", "Substitui um ID antigo por um oficial (De ➜ Para).", "bright_cyan"),
        ("Z", "↩️ Desfazer Ação", "Desfaz a última substituição da sua sessão.", "bright_cyan"),
        ("E", "🚀 Atualizar Planilhas do Excel", "Aplica todas as substituições nos arquivos físicos.", "bright_green"),
        ("Q", "🚪 Salvar e Sair", "Salva o progresso no backup e encerra a ferramenta.", "bright_red")
    ]
    
    for tecla, titulo, desc, cor in opcoes:
        if not historico_acoes and tecla == "Z":
            ui.print(f"   [dim]> [ {tecla} ] {titulo}[/dim]\n           [dim]{desc} (Histórico Vazio)[/dim]\n")
        else:
            ui.print(f"   [bold {cor}]>[/bold {cor}] [bold bright_white][ {tecla} ][/bold bright_white] [bold {cor}]{titulo}[/bold {cor}]\n           [dim white]{desc}[/dim white]\n")
            
    ui.print("[dim]" + "─" * 85 + "[/dim]")
    ui.print("   [bold bright_cyan]>[/bold bright_cyan] [blink]Aguardando comando...[/blink] ", end="")

# =========================================================================
# MOTOR PRINCIPAL
# =========================================================================

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
        
        for f in fornecedores:
            if not hasattr(f, 'movimentacoes_por_loja'): f.movimentacoes_por_loja = {}
            f.movimentacoes_originais = f.movimentacoes
            f.movimentacoes_por_loja_originais = f.movimentacoes_por_loja.copy()
        
        if os.path.exists(ARQUIVO_BACKUP):
            try:
                with open(ARQUIVO_BACKUP, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    
                sessao_atual_raw = dados.get("sessao_atual", {})
                historico_raw = dados.get("historico", [])

                if historico_raw:
                    for acao_raw in historico_raw:
                        tipo = acao_raw.get('tipo', 'M')
                        grupo_idx = acao_raw.get('grupo_idx', 'RECUPERADO')
                        dest_id = acao_raw.get('dest_fornecedor_id')
                        dest_forn = duplicate_service.buscar_por_id(dest_id, fornecedores) if dest_id else None
                        
                        alvos_objs = [duplicate_service.buscar_por_id(aid, fornecedores) for aid in acao_raw.get('alvos_ids', [])]
                        alvos_objs = [obj for obj in alvos_objs if obj]
                        
                        if not alvos_objs: continue
                        
                        if tipo in ['S', 'I', 'M']:
                            aplicar_migracao_em_lote(alvos_objs, dest_id, dest_forn, migration_service, sessao_atual, ids_processados, historico_acoes, tipo, grupo_idx)
                        elif tipo == 'P':
                            aplicar_pulo_em_lote(alvos_objs, ids_processados, historico_acoes, grupo_idx)
                elif sessao_atual_raw:
                    for orig, dest in sessao_atual_raw.items():
                        f_orig = duplicate_service.buscar_por_id(orig, fornecedores)
                        f_dest = duplicate_service.buscar_por_id(dest, fornecedores)
                        if f_orig:
                            aplicar_migracao_em_lote([f_orig], dest, f_dest, migration_service, sessao_atual, ids_processados, historico_acoes, 'M', 'RECUPERADO')

            except Exception as e:
                utils_console.erro(f"Erro ao ler backup anterior: {e}")

        atualizar_pendencias_grupos(grupos_duplicados, ids_processados)

        while True:
            pendentes_auto = sum(1 for g in grupos_duplicados if len(g.itens_pendentes) > 0)
            renderizar_hub_ui(pendentes_auto, len(sessao_atual), len(historico_acoes) > 0)
            
            tecla_hub = msvcrt.getch().upper()

            if tecla_hub == b'1':
                if pendentes_auto == 0:
                    limpar_tela_hard()
                    utils_console.sucesso("\nNão há grupos automáticos pendentes.")
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
                            limpar_tela_hard()
                            ui.print(Panel("[bold bright_yellow]VIAGEM NO TEMPO (RETROCEDER GRUPOS)[/bold bright_yellow]", border_style="bright_yellow"))
                            grupos_com_historico = sorted(list(set(a['grupo_idx'] for a in historico_acoes if isinstance(a['grupo_idx'], int))))
                            
                            if not grupos_com_historico:
                                ui.print("\n[bold bright_yellow][AVISO][/bold bright_yellow] Não há histórico para retroceder.")
                                time.sleep(2)
                                continue
                                
                            ui.print("[bold bright_white]Ações reversíveis nos seguintes grupos:[/bold bright_white]\n")
                            for g_idx in grupos_com_historico:
                                g_nome = grupos_duplicados[g_idx].nome
                                ui.print(f" [bold bright_cyan]➜[/bold bright_cyan] Grupo {g_idx + 1}: [bright_white]{escape(g_nome)}[/bright_white]")
                                
                            ui.print("\n[bold bright_white]NÚMERO do Grupo para voltar (ENTER cancela): [/bold bright_white]", end="")
                            alvo_str = input().strip()
                            if not alvo_str.isdigit(): continue
                                
                            target_idx = int(alvo_str) - 1
                            if target_idx not in grupos_com_historico: continue
                            
                            acoes_desfeitas = 0
                            while historico_acoes and isinstance(historico_acoes[-1]['grupo_idx'], int) and historico_acoes[-1]['grupo_idx'] >= target_idx:
                                u_acao = historico_acoes.pop()
                                reverter_acao(u_acao, sessao_atual, ids_processados, migration_service)
                                acoes_desfeitas += 1
                                
                            atualizar_pendencias_grupos(grupos_duplicados, ids_processados)
                            salvar_progresso(sessao_atual, historico_acoes)
                            marcados.clear()
                            utils_console.sucesso(f"\nRollback concluído! {acoes_desfeitas} ação(ões) desfeita(s).")
                            time.sleep(2)
                            idx_grupo = target_idx
                            break

                        elif acao == 'Z':
                            u_acao = historico_acoes.pop()
                            reverter_acao(u_acao, sessao_atual, ids_processados, migration_service)
                            atualizar_pendencias_grupos(grupos_duplicados, ids_processados)
                            salvar_progresso(sessao_atual, historico_acoes)
                            marcados.clear()
                            utils_console.sucesso("\nDesfeito com sucesso!")
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
                            aplicar_pulo_em_lote(alvos, ids_processados, historico_acoes, idx_grupo)
                            atualizar_pendencias_grupos(grupos_duplicados, ids_processados)
                            salvar_progresso(sessao_atual, historico_acoes)
                            marcados.clear()

                        elif acao == 'S':
                            if exibir_confirmacao_migracao(alvos, grupo.mestre.id, grupo.mestre.nome, grupo.mestre):
                                aplicar_migracao_em_lote(alvos, grupo.mestre.id, grupo.mestre, migration_service, sessao_atual, ids_processados, historico_acoes, 'S', idx_grupo)
                                atualizar_pendencias_grupos(grupos_duplicados, ids_processados)
                                salvar_progresso(sessao_atual, historico_acoes)
                                marcados.clear()

                        elif acao == 'T':
                            limpar_tela_hard()
                            ui.print(Panel("[bold bright_cyan]TRAZER FORNECEDOR PARA O GRUPO[/bold bright_cyan]", border_style="bright_cyan"))
                            ui.print("\n[bold bright_cyan]>[/bold bright_cyan] Digite o ID ou parte do Nome para pesquisar (ENTER p/ cancelar): ", end="")
                            busca = input().strip()
                            if not busca: continue
                            
                            escolhas = []
                            dest_forn = duplicate_service.buscar_por_id(busca, fornecedores)
                            
                            if dest_forn:
                                escolhas = [dest_forn]
                            else:
                                resultados = duplicate_service.buscar_por_nome_parcial(busca, fornecedores)
                                if resultados:
                                    pendentes_ids = {f.id for f in grupo.itens_pendentes}
                                    escolhas = menu_pesquisa_multi(resultados, busca, sessao_atual, ids_processados, pendentes_ids)
                                    if not escolhas: continue
                                else:
                                    ui.print("\n[bold bright_yellow][AVISO][/bold bright_yellow] Nenhum fornecedor encontrado com esse nome/ID.")
                                    time.sleep(1.5)
                                    continue
                            
                            adicionados = 0
                            for escolha in escolhas:
                                if escolha.id in ids_processados:
                                    ui.print(f"\n[bold bright_yellow][AVISO][/bold bright_yellow] O ID {escolha.id} já foi processado nesta sessão!")
                                    time.sleep(1)
                                    continue
                                    
                                if any(f.id == escolha.id for f in grupo.itens_pendentes):
                                    ui.print(f"\n[bold bright_yellow][AVISO][/bold bright_yellow] O ID {escolha.id} já está na lista deste grupo!")
                                    time.sleep(1)
                                    continue
                                    
                                grupo.itens_pendentes.append(escolha)
                                if escolha not in grupo.duplicados:
                                    grupo.duplicados.append(escolha)
                                adicionados += 1
                                
                            if adicionados > 0:
                                utils_console.sucesso(f"\n{adicionados} fornecedor(es) puxado(s) para este grupo!")
                                time.sleep(1.5)

                        elif acao == 'I':
                            limpar_tela_hard()
                            ui.print(Panel("[bold bright_cyan]SUBSTITUIR SELEÇÃO POR OUTRO ID[/bold bright_cyan]", border_style="bright_cyan"))
                            ui.print("\n[bold bright_cyan]>[/bold bright_cyan] Digite o ID exato OU parte do Nome (ENTER p/ cancelar): ", end="")
                            busca = input().strip()
                            if not busca: continue
                                
                            dest_id = None
                            dest_forn = duplicate_service.buscar_por_id(busca, fornecedores)
                            
                            if dest_forn:
                                dest_id = dest_forn.id
                                nome_dest = dest_forn.nome
                            else:
                                resultados = duplicate_service.buscar_por_nome_parcial(busca, fornecedores)
                                if resultados:
                                    escolha = menu_pesquisa_nativo(resultados, busca, sessao_atual, ids_processados)
                                    if escolha is None: continue
                                    elif escolha == "EXTERNO":
                                        dest_id = busca
                                        nome_dest = "ID EXTERNO"
                                    else:
                                        dest_forn = escolha
                                        dest_id = dest_forn.id
                                        nome_dest = dest_forn.nome
                                else:
                                    ui.print(f"\n[bold red][AVISO][/bold red] Nada encontrado com '{escape(busca)}'.")
                                    ui.print("[bold bright_white]Forçar uso como ID externo? (S/N): [/bold bright_white]", end="")
                                    if input().strip().upper() == 'S':
                                        dest_id = busca
                                        nome_dest = "ID EXTERNO"
                                    else: continue

                            if dest_id:
                                if exibir_confirmacao_migracao(alvos, dest_id, nome_dest, dest_forn):
                                    aplicar_migracao_em_lote(alvos, dest_id, dest_forn, migration_service, sessao_atual, ids_processados, historico_acoes, 'I', idx_grupo)
                                    atualizar_pendencias_grupos(grupos_duplicados, ids_processados)
                                    salvar_progresso(sessao_atual, historico_acoes)
                                    marcados.clear()

                    if voltar_pro_hub: break
                    if len(grupo.itens_pendentes) == 0: idx_grupo += 1

            elif tecla_hub == b'2':
                limpar_tela_hard()
                ui.print(Panel("[bold bright_cyan]SUBSTITUIÇÃO MANUAL LIVRE (DE ➜ PARA)[/bold bright_cyan]", border_style="bright_cyan"))
                ui.print("[bold bright_white]PASSO 1: Qual ID Antigo será removido das planilhas? (Origem)[/bold bright_white]")
                ui.print("Digite o Nome ou ID (ENTER p/ cancelar): ", end="")
                busca_origem = input().strip()
                if not busca_origem: continue
                
                resultados_orig = duplicate_service.buscar_por_nome_parcial(busca_origem, fornecedores)
                if not resultados_orig: continue
                    
                origem = menu_pesquisa_nativo(resultados_orig, busca_origem, sessao_atual, ids_processados)
                if origem == "EXTERNO" or origem is None: continue
                
                if origem.id in ids_processados:
                    ui.print("\n[bold bright_yellow][AVISO][/bold bright_yellow] Este ID já foi processado nesta sessão. Use o Ctrl+Z se precisar alterar.")
                    time.sleep(2)
                    continue

                limpar_tela_hard()
                ui.print(Panel("[bold bright_cyan]SUBSTITUIÇÃO MANUAL LIVRE (DE ➜ PARA)[/bold bright_cyan]", border_style="bright_cyan"))
                ui.print(f"[bold bright_green]ID ANTIGO (SERÁ SUBSTITUÍDO):[/bold bright_green] {origem.id} | {escape(origem.nome)} ({origem.movimentacoes} ocorrências)\n")
                
                ui.print("[bold bright_white]PASSO 2: Qual será o NOVO ID Oficial nessas linhas? (Destino)[/bold bright_white]")
                ui.print("Digite o Nome ou ID (ENTER p/ cancelar): ", end="")
                busca_dest = input().strip()
                if not busca_dest: continue

                dest_id = None
                dest_forn = duplicate_service.buscar_por_id(busca_dest, fornecedores)
                
                if dest_forn:
                    dest_id = dest_forn.id
                    nome_dest = dest_forn.nome
                else:
                    resultados_dest = duplicate_service.buscar_por_nome_parcial(busca_dest, fornecedores)
                    if resultados_dest:
                        escolha = menu_pesquisa_nativo(resultados_dest, busca_dest, sessao_atual, ids_processados)
                        if escolha is None: continue
                        elif escolha == "EXTERNO":
                            dest_id = busca_dest
                            nome_dest = "ID EXTERNO"
                        else:
                            dest_forn = escolha
                            dest_id = dest_forn.id
                            nome_dest = dest_forn.nome
                    else: continue
                
                if dest_id:
                    if exibir_confirmacao_migracao([origem], dest_id, nome_dest, dest_forn):
                        aplicar_migracao_em_lote([origem], dest_id, dest_forn, migration_service, sessao_atual, ids_processados, historico_acoes, 'M', 'MANUAL')
                        atualizar_pendencias_grupos(grupos_duplicados, ids_processados)
                        salvar_progresso(sessao_atual, historico_acoes)

            elif tecla_hub == b'Z' and historico_acoes:
                u_acao = historico_acoes.pop()
                reverter_acao(u_acao, sessao_atual, ids_processados, migration_service)
                atualizar_pendencias_grupos(grupos_duplicados, ids_processados)
                salvar_progresso(sessao_atual, historico_acoes)
                limpar_tela_hard()
                utils_console.sucesso("\nÚltima ação desfeita com sucesso!")
                time.sleep(1)

            elif tecla_hub == b'E':
                todas_migracoes = migration_service.obter_migracoes()
                if todas_migracoes:
                    limpar_tela_hard()
                    ui.print(Panel("[bold bright_green]🚀 ATUALIZANDO EXCEL E GERANDO RELATÓRIO[/bold bright_green]", expand=False))
                    print(f"Buscando e substituindo {len(todas_migracoes)} IDs nos arquivos originais...")
                    
                    excel_service.atualizar_ids(todas_migracoes)
                    falhas = excel_service.validar_migracoes(todas_migracoes)
                    arquivos_salvos = excel_service.salvar_planilhas()
                    
                    ids_mortos = [m.origem for m in todas_migracoes]
                    with open("RELATORIO_EXCLUSAO.txt", "w", encoding="utf-8") as f:
                        f.write("=== FORNECEDORES DESCONTINUADOS ===\n")
                        f.write("As linhas contendo estes IDs foram atualizadas com sucesso.\n")
                        f.write("Eles já não existem nas planilhas de movimentação e podem ser deletados da base:\n\n")
                        for m in todas_migracoes:
                            f.write(f"ID DESCARTADO: {m.origem}  ---> (Substituído por: {m.destino})\n")
                    
                    print(f"\n>> Relatório gerado: RELATORIO_EXCLUSAO.txt")
                    arquivo_fornecedores_limpo = excel_service.salvar_base_fornecedores_limpa(ids_mortos)
                    report_service.mostrar_validacao(falhas, arquivos_salvos, arquivo_fornecedores_limpo)
                    sys.exit()
                else:
                    limpar_tela_hard()
                    utils_console.sucesso("\nNenhuma alteração na fila. Os arquivos do Excel permanecem intocados.")
                    time.sleep(2)

            elif tecla_hub == b'Q':
                limpar_tela_hard()
                utils_console.sucesso("\nProgresso salvo com segurança em 'backup_sessao.json'. Até mais!")
                sys.exit()

    except KeyboardInterrupt:
        utils_console.erro("\nExecução cancelada pelo usuário (Ctrl+C).")
    except Exception as e:
        utils_console.erro(f"\nFalha na execução do fluxo: {str(e)}")

if __name__ == "__main__":
    main()