from services.excel_service import ExcelService
from services.duplicate_service import DuplicateService
from services.report_service import ReportService
from utils import console

def main():
    excel_service = ExcelService()
    duplicate_service = DuplicateService()
    report_service = ReportService()

    try:
        excel_service.abrir_planilhas()
        
        fornecedores = excel_service.ler_fornecedores()
        contagem = excel_service.contar_movimentacoes()
        
        grupos_duplicados = duplicate_service.encontrar_duplicados(fornecedores, contagem)
        
        report_service.mostrar_relatorio(grupos_duplicados)
        
    except Exception as e:
        console.erro(f"Falha na execução do fluxo: {str(e)}")

if __name__ == "__main__":
    main()