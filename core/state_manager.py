import json
import os

class StateManager:
    def __init__(self, arquivo_backup):
        self.arquivo_backup = arquivo_backup
        self.sessao_atual = {}
        self.historico_acoes = []
        self.ids_processados = set()

    def salvar_progresso(self):
        """ Salva o estado atual no arquivo JSON de backup """
        historico_serializado = []
        for acao in self.historico_acoes:
            historico_serializado.append({
                'tipo': acao['tipo'],
                'grupo_idx': acao['grupo_idx'],
                'alvos_ids': [a['obj'].id for a in acao['alvos']],
                'dest_fornecedor_id': acao['dest_fornecedor'].id if acao.get('dest_fornecedor') else None
            })
        dados = {"sessao_atual": self.sessao_atual, "historico": historico_serializado}
        with open(self.arquivo_backup, "w", encoding="utf-8") as out:
            json.dump(dados, out, ensure_ascii=False, indent=4)

    def carregar_backup(self, fornecedores, duplicate_service, migration_service):
        """ Tenta restaurar a sessão a partir do arquivo JSON na inicialização """
        if os.path.exists(self.arquivo_backup):
            try:
                with open(self.arquivo_backup, "r", encoding="utf-8") as f:
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
                            self.aplicar_migracao_em_lote(alvos_objs, dest_id, dest_forn, migration_service, tipo, grupo_idx, restaurando_backup=True)
                        elif tipo == 'P': 
                            self.aplicar_pulo_em_lote(alvos_objs, grupo_idx, restaurando_backup=True)
                            
                elif sessao_atual_raw:
                    for orig, dest in sessao_atual_raw.items():
                        f_orig = duplicate_service.buscar_por_id(orig, fornecedores)
                        f_dest = duplicate_service.buscar_por_id(dest, fornecedores)
                        if f_orig: 
                            self.aplicar_migracao_em_lote([f_orig], dest, f_dest, migration_service, 'M', 'RECUPERADO', restaurando_backup=True)

            except Exception as e:
                print(f"Erro ao ler backup anterior: {e}")

    def aplicar_migracao_em_lote(self, alvos, dest_id, dest_forn, migration_service, tipo, grupo_idx, restaurando_backup=False):
        """ Executa uma substituição e guarda na memória """
        alvos_data = []
        for f in alvos:
            if f.id == dest_id: continue
            alvos_data.append({'obj': f, 'movs': f.movimentacoes, 'lojas': f.movimentacoes_por_loja.copy()})
            migration_service.criar_migracao_individual(f, dest_id)
            self.sessao_atual[f.id] = dest_id
            self.ids_processados.add(f.id)
            
            if dest_forn:
                dest_forn.movimentacoes += f.movimentacoes
                for loja, qtd in f.movimentacoes_por_loja.items():
                    dest_forn.movimentacoes_por_loja[loja] = dest_forn.movimentacoes_por_loja.get(loja, 0) + qtd
                    
            f.movimentacoes = 0
            f.movimentacoes_por_loja = {}

        if alvos_data:
            self.historico_acoes.append({'tipo': tipo, 'grupo_idx': grupo_idx, 'alvos': alvos_data, 'dest_fornecedor': dest_forn})
            
        if not restaurando_backup:
            self.salvar_progresso()

    def aplicar_pulo_em_lote(self, alvos, grupo_idx, restaurando_backup=False):
        """ Guarda a ação de Pular no histórico """
        alvos_data = []
        for f in alvos:
            alvos_data.append({'obj': f})
            self.ids_processados.add(f.id)
            
        if alvos_data:
            self.historico_acoes.append({'tipo': 'P', 'grupo_idx': grupo_idx, 'alvos': alvos_data, 'dest_fornecedor': None})
        
        if not restaurando_backup:
            self.salvar_progresso()

    def reverter_acao(self, u_acao, migration_service):
        """ A Mágica do Ctrl+Z: Devolve as quantidades exatas de onde elas vieram """
        dest_f = u_acao['dest_fornecedor']
        if u_acao['tipo'] in ['S', 'I', 'M']:
            for alvo_data in u_acao['alvos']:
                f = alvo_data['obj']
                t_movs = alvo_data['movs']
                t_lojas = alvo_data['lojas']
                migration_service.remover_migracao_individual(f.id)
                
                if f.id in self.sessao_atual: del self.sessao_atual[f.id]
                self.ids_processados.discard(f.id)
                
                if dest_f and f.id != dest_f.id: 
                    dest_f.movimentacoes -= t_movs
                    for loja, qtd in t_lojas.items():
                        dest_f.movimentacoes_por_loja[loja] -= qtd
                        if dest_f.movimentacoes_por_loja[loja] <= 0: del dest_f.movimentacoes_por_loja[loja]
                            
                f.movimentacoes = t_movs
                f.movimentacoes_por_loja = t_lojas.copy()
                
        elif u_acao['tipo'] == 'P':
            for alvo_data in u_acao['alvos']: 
                self.ids_processados.discard(alvo_data['obj'].id)
        
        self.salvar_progresso()

    def atualizar_pendencias_grupos(self, grupos_duplicados):
        """ Atualiza visualmente as listas de conflitos """
        for grupo in grupos_duplicados:
            grupo.itens_pendentes = [f for f in grupo.duplicados if f.id not in self.ids_processados]