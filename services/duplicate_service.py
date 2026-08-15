import config
from difflib import SequenceMatcher

class GrupoDuplicatas:
    """ Objeto que empacota o Registro Mestre e suas duplicatas para a interface """
    def __init__(self, mestre, duplicados, motivo):
        self.mestre = mestre
        self.duplicados = duplicados
        self.itens_pendentes = duplicados.copy()
        self.motivo = motivo
        self.nome = mestre.nome

class DuplicateService:
    def __init__(self, modo):
        self.modo = modo
        
        # Puxa dinamicamente o nível de rigor que você definiu no painel de controle
        if self.modo == 1:
            self.limiar = config.SIMILARIDADE_FORNECEDORES / 100.0
        else:
            self.limiar = config.SIMILARIDADE_PRODUTOS / 100.0

    def calcular_similaridade(self, str1, str2):
        """ Retorna uma porcentagem (0.0 a 1.0) de quão idênticos são dois textos """
        if not str1 or not str2:
            return 0.0
        # O SequenceMatcher faz o alinhamento de blocos de caracteres idênticos
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
        
    def _limpar_texto(self, texto):
        """ Remove espaços em branco nas pontas e deixa tudo maiúsculo para não falhar por Case Sensitivity """
        return str(texto).strip().upper()

    def encontrar_duplicados(self, registros, contagem):
        """ 
        O Cérebro da Operação Automática:
        1. Injeta os dados da varredura nos registros
        2. Ordena quem é o item mais importante (mestre)
        3. Compara o mestre com o resto da lista para achar clones
        """
        # Passo 1: Atualiza os registros oficiais com as ocorrências reais encontradas nas tabelas filhas
        for reg in registros:
            if reg.id in contagem:
                reg.movimentacoes_por_loja = contagem[reg.id].copy()
                reg.movimentacoes = sum(reg.movimentacoes_por_loja.values())
            else:
                reg.movimentacoes = 0
                reg.movimentacoes_por_loja = {}

        grupos = []
        processados = set()
        
        # A lógica do "Mestre": O item que tiver MAIS notas lançadas ganha o título de oficial.
        # Em caso de empate de notas, usa a ordem alfabética do nome para desempatar.
        registros_ordenados = sorted(registros, key=lambda x: (x.movimentacoes, x.nome), reverse=True)
        
        # Passo 2: A Varredura Combinatória
        for i, reg_mestre in enumerate(registros_ordenados):
            if reg_mestre.id in processados:
                continue
                
            duplicados_grupo = []
            nome_mestre_limpo = self._limpar_texto(reg_mestre.nome)
            
            # Ignora anomalias sem nome, impedindo que o assistente tente agrupar vários itens vazios
            if nome_mestre_limpo == "SEM NOME" or not nome_mestre_limpo:
                continue
            
            for reg_candidato in registros_ordenados[i+1:]:
                if reg_candidato.id in processados:
                    continue
                    
                nome_candidato_limpo = self._limpar_texto(reg_candidato.nome)
                
                if nome_candidato_limpo == "SEM NOME" or not nome_candidato_limpo:
                    continue
                
                # Passo 3: O Teste de DNA
                similaridade = self.calcular_similaridade(nome_mestre_limpo, nome_candidato_limpo)
                
                # Se a similaridade for maior ou igual a régua do config.py (ex: 95% para produtos)
                if similaridade >= self.limiar:
                    duplicados_grupo.append(reg_candidato)
                    processados.add(reg_candidato.id)
            
            if duplicados_grupo:
                processados.add(reg_mestre.id)
                porcentagem_tela = int(self.limiar * 100)
                motivo = f"Similaridade do Nome >= {porcentagem_tela}%"
                
                grupo = GrupoDuplicatas(reg_mestre, duplicados_grupo, motivo)
                grupos.append(grupo)
                
        return grupos

    def buscar_por_id(self, busca_id, registros):
        """ O motor de busca rápida exata acionado quando você digita um ID Manual """
        busca_id = str(busca_id).strip()
        for r in registros:
            if str(r.id).strip() == busca_id:
                return r
        return None

    def buscar_por_nome_parcial(self, termo, registros):
        """ O motor de busca flexível acionado quando você digita partes de um nome """
        termo = str(termo).strip().lower()
        resultados = []
        for r in registros:
            if termo in r.nome.lower() or termo in str(r.id).lower():
                resultados.append(r)
        return resultados