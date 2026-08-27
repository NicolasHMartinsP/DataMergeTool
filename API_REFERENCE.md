# Referência da API Interna (DataMergeTool v8.0)

Este documento destina-se a desenvolvedores e engenheiros de software que irão estender ou dar manutenção no código-fonte. A API interna está encapsulada nos módulos de Serviço (Services) e Gerenciamento de Estado (Core).

## 1. Módulo Core (`core/state_manager.py`)

A classe `StateManager` é a entidade central que orquestra a sessão do usuário e o histórico de modificações para o sistema de _Rollback_ (Desfazer).

- `__init__(self, backup_file: str)`: Inicializa o gerenciador definindo o arquivo onde o JSON de backup será persistido.
- `save_state(self)`: Serializa e salva a sessão ativa (`current_session`) e o histórico (`action_history`) em formato JSON.
- `load_backup(self, entities, duplicate_service, migration_service)`: Analisa e restaura os objetos processados a partir do backup JSON para evitar perda de dados.
- `apply_batch_migration(self, targets, dest_id, dest_entity, migration_service, action_type, group_idx, is_restoring=False)`: Aplica a transformação do ID de um grupo alvo (`targets`) para um ID Mestre (`dest_id`), contabiliza as chaves lógicas na matriz de entidades e salva a ação no histórico.
- `apply_batch_skip(self, targets, group_idx, is_restoring=False)`: Registra um ou múltiplos itens como ignorados, retirando-os da fila de análise do assistente.
- `undo_last_action(self, action_payload, migration_service)`: Recupera a última ação baseada na pilha (LIFO). Devolve as quantidades de transações para seus donos originais e anula a migração.
- `update_group_pending_items(self, duplicate_groups)`: Atualiza a lista visual dos módulos garantindo que itens recém-processados sejam removidos do assistente visual.

## 2. Módulo de Serviços (`services/`)

### 2.1. ExcelService (`excel_service.py`)

Módulo de comunicação de I/O (Input/Output).

- `read_master_records(self, mode: int) -> List[Entity]`: Conecta-se à API do Google Sheets via OAuth2 e recupera as colunas oficiais estipuladas no arquivo de configuração, retornando uma lista de objetos `Entity`.
- `open_spreadsheets(self, mode: int)`: Inicializa a varredura local. Varre diretórios em busca de planilhas formatadas (`.xlsx`) compatíveis com a _Whitelist_ configurada.
- `count_transactions(self) -> dict`: Agrega e consolida contagens individuais (agrupando por `Loja > Aba > Coluna`) de cada identificador válido lido nos arquivos locais.
- `apply_id_updates(self, migrations)`: Desce o lote contendo o De-Para de migrações nos objetos instanciados do `openpyxl`.
- `validate_migrations(self, migrations) -> List[str]`: Retorna uma matriz de mensagens de erros rastreando se algum ID de origem permaneceu residualmente na planilha.
- `save_workbooks(self) -> List[str]`: Despeja o estado final dos arquivos formatados em buffers de saída separados (`saida/Movimentacoes_Atualizadas` e `saida/Contas_Atualizadas`).

### 2.2. DuplicateService (`duplicate_service.py`)

Inteligência e mineração de dados.

- `find_duplicates(self, records, transaction_counts) -> List[DuplicateGroup]`: Algoritmo de agrupamento relacional. Identifica entidades de nomes sintaticamente parecidos usando `SequenceMatcher`.
- `calculate_similarity(self, str1, str2) -> float`: Wrapper em torno do comparador que retorna um coeficiente de similariedade (0.0 a 1.0).
- `find_by_id(self, search_id: str, records) -> Entity`: Pesquisa unitária exata $O(N)$ em memória (retorna o objeto `Entity`).
- `search_by_partial_name(self, term: str, records) -> List[Entity]`: Pesquisa fuzzy simplificada retornando a matriz de resultados correspondentes via string parsing (ID e Nome).

### 2.3. CrossService (`cross_service.py`)

Engenharia relacional para referências cruzadas.

- `scan_referential_integrity(self, workbooks, master_records) -> List[dict]`: Rotina de análise. Vasculha a matriz relacional (Chave Estrangeira 'Nota/ID') em tabelas dependentes (Contas e Compras). Emite um vetor dicionário contendo conflitos lógicos a serem resolvidos.
- `apply_resolution(self, conflict, new_id: str)`: Modifica em tempo de execução a interface de célula virtual da linha conflitante, sincronizando os lados divergentes.

### 2.4. MigrationService (`migration_service.py`)

Repositório em cache do _Migration Schema_.

- `create_individual_migration(self, source: Entity, target_id: str)`: Cadastra o De-Para, assegurando via sobrescrita que não há duplicação de ordens na mesma entidade de origem.
- `remove_individual_migration(self, source_id: str)`: Limpa a transição cadastrada (Gatilho utilitário usado durante eventos de _Undo_).

## 3. Considerações de Configuração (`config.py`)

A API reflete diretamente o arquivo de constantes `config.py`. Nenhuma referência a chaves "hardcoded" (colunas e nomes de abas) deve existir fora deste documento. O sistema agora é 100% genérico.
As porcentagens de rigidez do Algoritmo Combinatório (`MODE_1_SIMILARITY_THRESHOLD` e `MODE_2_SIMILARITY_THRESHOLD`) delimitam rigorosamente o comportamento do `DuplicateService.find_duplicates`.
