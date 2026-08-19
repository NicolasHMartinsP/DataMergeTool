import config
from collections import defaultdict

class CrossService:
    def __init__(self):
        self.total_resolvidos = 0
        pass

    def escanear_integridade(self, workbooks, fornecedores_oficiais):
        """ Varre os arquivos na memória e cruza as Notas com Contas a Pagar com segurança máxima """
        master_ids = {str(f.id).strip().lower(): f for f in fornecedores_oficiais}
        map_notas = defaultdict(lambda: {'contas': [], 'notas': []})
        
        # 1. VARREDURA BLINDADA (Regras Estritas)
        for arquivo, wb in workbooks.items():
            for aba_nome in wb.sheetnames:
                aba = wb[aba_nome]
                aba_upper = aba_nome.upper().strip()
                
                tipo_aba = None
                col_link_name = ""
                col_forn_name = "FORNECEDOR"
                
                # Regras cravadas conforme a sua estrutura de colunas
                if "CONTAS A PAGAR" in aba_upper:
                    tipo_aba = 'CONTAS'
                    col_link_name = "NOTA"
                elif "NOTAS DE COMPRA" in aba_upper or "NOTAS DE COMPRAS" in aba_upper:
                    tipo_aba = 'NOTAS'
                    col_link_name = "ID"
                elif "NOTAS" == aba_upper or "NOTAS " in aba_upper: 
                    tipo_aba = 'NOTAS'
                    col_link_name = "ID"
                else:
                    continue
                    
                # Extrai a primeira linha (cabeçalhos)
                header = [str(c.value).strip().upper() if c.value else "" for c in aba[1]]
                
                col_link_idx = -1
                col_forn_idx = -1
                
                # MIRA LASER: Procura o nome EXATO, sem adivinhação
                for i, h in enumerate(header):
                    if h == col_link_name:
                        col_link_idx = i + 1
                    if h == col_forn_name:
                        col_forn_idx = i + 1
                        
                # Se não achou exato, desiste desta aba e não tenta inventar
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
                        'cell': cell_forn
                    }
                    
                    if tipo_aba == 'CONTAS':
                        map_notas[val_link]['contas'].append(dado)
                    else:
                        map_notas[val_link]['notas'].append(dado)
                        
        # 2. ANÁLISE DE DIVERGÊNCIAS
        conflitos = []
        for id_nota, dados in map_notas.items():
            if not dados['contas'] or not dados['notas']: 
                continue 
            
            # SISTEMA ANTIBUG: Se o AppSheet gerou duas linhas pra mesma nota (uma vazia e uma preenchida), 
            # o robô filtra as vazias e prioriza a preenchida para não te dar alarme falso.
            contas_preenchidas = [c for c in dados['contas'] if c['val'] != ""]
            c_conta = contas_preenchidas[0] if contas_preenchidas else dados['contas'][0]
            
            notas_preenchidas = [n for n in dados['notas'] if n['val'] != ""]
            c_nota = notas_preenchidas[0] if notas_preenchidas else dados['notas'][0]
            
            id_c = c_conta['val'].lower()
            id_n = c_nota['val'].lower()
            
            # IGNORA LANÇAMENTOS DO SISTEMA (Vazios de ambos os lados)
            if id_c == "" and id_n == "":
                continue
            
            # SE ESTÃO IGUAIS E SÃO OFICIAIS, ESTÁ 100% CORRETO E ELE PULA.
            if id_c == id_n and id_c in master_ids: 
                continue
            
            def get_status(val):
                if not val: return "VAZIO"
                if val in master_ids: return "OFICIAL"
                return "FANTASMA"
                
            st_c = get_status(id_c)
            st_n = get_status(id_n)
            
            sugestao = None
            nome_sugestao = ""
            if st_c == "OFICIAL" and st_n != "OFICIAL": 
                sugestao = c_conta['val']
                nome_sugestao = master_ids[id_c].nome
            elif st_n == "OFICIAL" and st_c != "OFICIAL":
                sugestao = c_nota['val']
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
        """ Atualiza a célula real na memória do Python """
        conflito['conta']['cell'].value = novo_id
        conflito['nota']['cell'].value = novo_id
        self.total_resolvidos += 1