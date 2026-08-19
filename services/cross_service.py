import config
from collections import defaultdict

class CrossService:
    def __init__(self):
        # Puxa os nomes das colunas de identificação da Nota definidos no config.py
        self.col_link_contas = getattr(config, 'COLUNA_LINK_CONTAS', "Nota")
        self.col_link_notas = getattr(config, 'COLUNA_LINK_NOTAS', "ID")

    def escanear_integridade(self, workbooks, fornecedores_oficiais):
        """ Varre os arquivos na memória e cruza as Notas com Contas a Pagar """
        # Cria um dicionário rápido para saber quem é Oficial
        master_ids = {str(f.id).strip().lower(): f for f in fornecedores_oficiais}
        
        # Estrutura: { 'Numero_da_Nota': {'contas': [], 'notas': []} }
        map_notas = defaultdict(lambda: {'contas': [], 'notas': []})
        
        # 1. VARREDURA DE COLETA
        for arquivo, wb in workbooks.items():
            for aba_nome in wb.sheetnames:
                aba = wb[aba_nome]
                aba_upper = aba_nome.upper()
                
                is_contas = "CONTAS A PAGAR" in aba_upper
                is_notas = "NOTAS" in aba_upper or "NOTAS DE COMPRAS" in aba_upper
                
                if not is_contas and not is_notas: 
                    continue
                
                header = [str(c.value).strip().upper() if c.value else "" for c in aba[1]]
                col_link_idx = -1
                col_forn_idx = -1
                
                # Identifica as colunas dinamicamente
                for i, h in enumerate(header):
                    if is_contas and h == self.col_link_contas.upper(): col_link_idx = i + 1
                    elif is_notas and h == self.col_link_notas.upper(): col_link_idx = i + 1
                    
                    if "FORNECEDOR" in h: col_forn_idx = i + 1
                    
                if col_link_idx == -1 or col_forn_idx == -1: 
                    continue
                
                # Extrai os dados linha por linha
                for row in aba.iter_rows(min_row=2):
                    cell_link = row[col_link_idx - 1]
                    cell_forn = row[col_forn_idx - 1]
                    
                    val_link = str(cell_link.value).strip() if cell_link.value is not None else ""
                    if val_link.endswith(".0"): val_link = val_link[:-2]
                    if not val_link or val_link.lower() == "none": continue
                    
                    val_forn = str(cell_forn.value).strip() if cell_forn.value is not None else ""
                    if val_forn.endswith(".0"): val_forn = val_forn[:-2]
                    if val_forn.lower() == "none": val_forn = ""
                    
                    dado = {
                        'arquivo': arquivo,
                        'aba': aba_nome,
                        'row': cell_forn.row,
                        'val': val_forn,
                        'cell': cell_forn  # Guardamos a célula real para editar depois!
                    }
                    
                    if is_contas: map_notas[val_link]['contas'].append(dado)
                    elif is_notas: map_notas[val_link]['notas'].append(dado)
                    
        # 2. ANÁLISE DE DIVERGÊNCIAS
        conflitos = []
        for id_nota, dados in map_notas.items():
            if not dados['contas'] or not dados['notas']: 
                continue # Medida de Segurança: Ignora se a nota não existir dos dois lados
            
            c_conta = dados['contas'][0]
            c_nota = dados['notas'][0]
            
            id_c = c_conta['val'].lower()
            id_n = c_nota['val'].lower()
            
            # Se estão iguais e existem no The Best Almeida, está tudo 100% íntegro!
            if id_c == id_n and id_c in master_ids: 
                continue
            
            def get_status(val):
                if not val: return "VAZIO"
                if val in master_ids: return "OFICIAL"
                return "FANTASMA"
                
            st_c = get_status(id_c)
            st_n = get_status(id_n)
            
            # Inteligência: Define se há uma sugestão óbvia de correção
            sugestao = None
            nome_sugestao = ""
            if st_c == "OFICIAL" and st_n != "OFICIAL": 
                sugestao = c_conta['val'] # A Conta está certa, espelha para a Nota
                nome_sugestao = master_ids[id_c].nome
            elif st_n == "OFICIAL" and st_c != "OFICIAL":
                sugestao = c_nota['val'] # A Nota está certa, espelha para a Conta
                nome_sugestao = master_ids[id_n].nome
                
            conflitos.append({
                'id_nota': id_nota,
                'conta': c_conta,
                'nota': c_nota,
                'st_c': st_c,
                'st_n': st_n,
                'sugestao_id': sugestao,
                'sugestao_nome': nome_sugestao
            })
            
        return conflitos

    def selar_paz(self, conflito, novo_id):
        """ Atualiza a célula real na memória do Python simultaneamente em ambas as abas """
        conflito['conta']['cell'].value = novo_id
        conflito['nota']['cell'].value = novo_id