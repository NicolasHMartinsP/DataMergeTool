import sys
import msvcrt
import warnings
import traceback

from services.excel_service import ExcelService
from services.duplicate_service import DuplicateService
from services.report_service import ReportService
from services.migration_service import MigrationService
from services.cross_service import CrossService

from ui.views import UIView
from core.state_manager import StateManager
from utils.button_handlers import ButtonHandlers
from utils import console as utils_console

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

def normalize_id(val):
    s = str(val).strip().lower()
    return s[:-2] if s.endswith(".0") else s

def main():
    ui_view = UIView()
    import config
    selected_mode = ui_view.select_operation_mode()
    mode_name = getattr(config, 'MODE_1_NAME', 'Modo 1').upper() if selected_mode == 1 else getattr(config, 'MODE_2_NAME', 'Modo 2').upper()
    backup_file = f"backup_{mode_name.lower()}.json"

    state_manager = StateManager(backup_file)

    excel_service = ExcelService()
    duplicate_service = DuplicateService(selected_mode)
    report_service = ReportService()
    migration_service = MigrationService()
    cross_service = CrossService()
    
    try:
        excel_service.open_spreadsheets(selected_mode)
        records = excel_service.read_master_records(selected_mode)
    except Exception as e:
        ui_view.show_critical_error(traceback.format_exc())
        sys.exit(1)

    raw_counts = excel_service.count_transactions()

    for record in records:
        record.id = normalize_id(record.id)

    transaction_counts = {}
    for k, v in raw_counts.items():
        k_norm = normalize_id(k)
        if k_norm not in transaction_counts: 
            transaction_counts[k_norm] = {}
        for loc, qty in v.items():
            transaction_counts[k_norm][loc] = transaction_counts[k_norm].get(loc, 0) + qty

    duplicate_groups = duplicate_service.find_duplicates(records, transaction_counts)
    
    for record in records:
        if not hasattr(record, 'transactions_by_store'): 
            record.transactions_by_store = {}
        record.original_transactions_count = record.transactions_count
        record.original_transactions_by_store = record.transactions_by_store.copy()

    state_manager.load_backup(records, duplicate_service, migration_service)
    state_manager.update_group_pending_items(duplicate_groups)

    handlers = ButtonHandlers(
        ui_view=ui_view,
        state_manager=state_manager,
        excel_service=excel_service,
        duplicate_service=duplicate_service,
        migration_service=migration_service,
        report_service=report_service,
        cross_service=cross_service,
        records=records,
        counts=transaction_counts,
        duplicate_groups=duplicate_groups,
        mode_name=mode_name
    )

    while True:
        pending = sum(1 for g in duplicate_groups if len(g.pending_items) > 0)
        
        ui_view.render_hub_ui(
            pending, 
            len(state_manager.current_session), 
            len(state_manager.action_history) > 0, 
            mode_name
        )
        
        key = msvcrt.getch().upper()

        if key == b'1': handlers.handle_automatic_resolution()
        elif key == b'2': handlers.handle_manual_substitution()
        elif key == b'3': handlers.handle_search()
        elif key == b'4': handlers.handle_orphan_audit()
        elif key == b'5': handlers.handle_inactive_cleanup()
        elif key == b'6': handlers.handle_cross_sync()
        elif key == b'Z': handlers.handle_undo()
        elif key == b'E': handlers.handle_export()
        elif key == b'Q': handlers.handle_exit()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        utils_console.print_error("\nExecução cancelada pelo usuário (Ctrl+C).")
    except Exception as e:
        utils_console.print_error(f"\nFalha na execução do fluxo: {str(e)}")