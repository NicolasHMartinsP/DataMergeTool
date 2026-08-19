import sys
import msvcrt
import warnings

# ==========================================
# IMPORTAÇÕES DOS SERVIÇOS (MÓDULOS BASE)
# ==========================================
from services.excel_service import ExcelService
from services.duplicate_service import DuplicateService
from services.report_service import ReportService
from services.migration_service import MigrationService
from services.cross_service import CrossService

# ==========================================
# IMPORTAÇÕES DA ARQUITETURA REFATORADA (MVC)
# ==========================================
from ui.views import UIView
from core.state_manager import StateManager
from utils.button_handlers import ButtonHandlers

# Mantendo o import do seu console utilitário de logs
from utils import console as utils_console

# Suprime os avisos chatos do openpyxl
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

def main():
    # 1. INICIALIZAÇÃO DA INTERFACE E MODO DE OPERAÇÃO
    ui_view = UIView()
    modo_selecionado = ui_view.selecionar_modo_operacao()
    modo_nome = "FORNECEDOR" if modo_selecionado == 1 else "PRODUTO"
    arquivo_backup = f"backup_{modo_nome.lower()}es.json"

    # 2. INICIALIZAÇÃO DO GERENCIADOR DE ESTADO (MEMÓRIA)
    state_manager = StateManager(arquivo_backup)

    # 3. INICIALIZAÇÃO DOS SERVIÇOS
    excel_service = ExcelService()
    duplicate_service = DuplicateService(modo_selecionado)
    report_service = ReportService()
    migration_service = MigrationService()
    cross_service = CrossService()
    
    # 4. CONEXÃO E LEITURA DE DADOS (O Boot do Sistema)
    try:
        excel_service.abrir_planilhas(modo_selecionado)
        fornecedores = excel_service.ler_fornecedores()
    except Exception as e:
        import traceback
        ui_view.exibir_erro_critico(traceback.format_exc())
        sys.exit(1)

    contagem_raw = excel_service.contar_movimentacoes()

    # ==============================================================
    # FILTRO DE NORMALIZAÇÃO DE IDs (Corrige ".0" e Case Sensitive)
    # ==============================================================
    def normalizar_id(valor):
        s = str(valor).strip().lower()
        return s[:-2] if s.endswith(".0") else s

    for f in fornecedores:
        f.id = normalizar_id(f.id)

    contagem = {}
    for k, v in contagem_raw.items():
        k_norm = normalizar_id(k)
        if k_norm not in contagem: 
            contagem[k_norm] = {}
        for loc, qtd in v.items():
            contagem[k_norm][loc] = contagem[k_norm].get(loc, 0) + qtd

    # 5. PREPARAÇÃO DOS DADOS E RECUPERAÇÃO DE SESSÃO
    grupos_duplicados = duplicate_service.encontrar_duplicados(fornecedores, contagem)
    
    for f in fornecedores:
        if not hasattr(f, 'movimentacoes_por_loja'): 
            f.movimentacoes_por_loja = {}
        f.movimentacoes_originais = f.movimentacoes
        f.movimentacoes_por_loja_originais = f.movimentacoes_por_loja.copy()

    # Pede para a memória tentar carregar o backup
    state_manager.carregar_backup(fornecedores, duplicate_service, migration_service)
    state_manager.atualizar_pendencias_grupos(grupos_duplicados)

    # 6. INJEÇÃO DE DEPENDÊNCIAS NOS BOTÕES (O Cérebro das Ações)
    handlers = ButtonHandlers(
        ui_view=ui_view,
        state_manager=state_manager,
        excel_service=excel_service,
        duplicate_service=duplicate_service,
        migration_service=migration_service,
        report_service=report_service,
        cross_service=cross_service,
        fornecedores=fornecedores,
        contagem=contagem,
        grupos_duplicados=grupos_duplicados,
        modo_nome=modo_nome
    )

    # ==========================================
    # LOOP PRINCIPAL (O Roteador do Sistema)
    # ==========================================
    while True:
        pendentes_auto = sum(1 for g in grupos_duplicados if len(g.itens_pendentes) > 0)
        
        # Pede para o UIView desenhar a tela inicial
        ui_view.renderizar_hub_ui(
            pendentes_auto, 
            len(state_manager.sessao_atual), 
            len(state_manager.historico_acoes) > 0, 
            modo_nome
        )
        
        # Escuta o teclado e joga a responsabilidade pro ButtonHandlers
        tecla_hub = msvcrt.getch().upper()

        if tecla_hub == b'1':
            handlers.acao_assistente_automatico()
        elif tecla_hub == b'2':
            handlers.acao_substituicao_manual()
        elif tecla_hub == b'3':
            handlers.acao_raiox_pesquisa()
        elif tecla_hub == b'4':
            handlers.acao_cacador_orfaos()
        elif tecla_hub == b'5':
            handlers.acao_limpar_peso_morto()
        elif tecla_hub == b'6':
            handlers.acao_sincronizador_cruzado()
        elif tecla_hub == b'Z':
            handlers.acao_desfazer()
        elif tecla_hub == b'E':
            handlers.acao_exportar_excel()
        elif tecla_hub == b'Q':
            handlers.acao_salvar_sair()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        utils_console.erro("\nExecução cancelada pelo usuário (Ctrl+C).")
    except Exception as e:
        utils_console.erro(f"\nFalha na execução do fluxo: {str(e)}")