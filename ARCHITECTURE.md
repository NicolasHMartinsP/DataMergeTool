# Arquitetura do DataMergeTool v8.0

O **DataMergeTool** é uma aplicação projetada para consolidar, validar e sincronizar registros (entidades flexíveis definidas no `config.py`) entre planilhas locais do Excel e uma base mestre hospedada na nuvem (Google Sheets).

## Visão Geral do Sistema (Modelo Híbrido)

A arquitetura do DataMergeTool v8.0 opera em um modelo híbrido:

1. **Cloud (Nuvem):** A base de dados mestre de leitura é mantida no Google Sheets, servindo como fonte da verdade (Source of Truth).
2. **Local:** Planilhas físicas em formato `.xlsx` que contêm movimentações diárias (ex: Contas a Pagar, Notas de Compra). O sistema atua nestas planilhas locais realizando substituições e correções estruturais baseadas na fonte da verdade.

## Padrão Arquitetural MVC

O projeto segue o padrão **Model-View-Controller (MVC)** para garantir a separação de responsabilidades e facilitar a manutenção e escalabilidade.

### 1. Model (Camada de Dados)

Localizada na pasta `models/`, representa as entidades de negócio.

- `Entity` (`entity.py`): Estrutura base de um registro genérico de negócio, mantendo suas propriedades e seu histórico de transações mapeado.
- `DuplicateGroup` (`duplicate_group.py`): Agrupador que vincula um registro mestre às suas duplicatas detectadas pela engine de similaridade.
- `Migration` (`migration.py`): Estrutura que registra as transformações de IDs, guardando a origem (ID antigo) e destino (ID novo) para o lote final.

### 2. View (Camada de Apresentação)

Localizada na pasta `ui/` e `utils/`.

- `UIView` (`views.py`): Responsável pela renderização de interfaces interativas, menus e tabelas (utilizando a biblioteca `rich`). A View não processa regras de negócio, apenas exibe os dados fornecidos pelo Controller e captura os inputs do usuário via teclado.
- `console.py`: Utilitário simples para exibições formatadas (títulos, avisos e mensagens de sucesso/erro).

### 3. Controller (Camada de Controle e Serviços)

Localizada nas pastas `core/` e `services/`, atuando como o cérebro da aplicação.

- `StateManager` (`core/state_manager.py`): Controla o ciclo de vida da sessão do usuário, permitindo salvar o estado no disco (`backup.json`), restaurar o progresso em caso de fechamento acidental e gerenciar a fila de ações (para a funcionalidade "Desfazer").
- **Services (`services/`)**: Regras de negócio encapsuladas.
  - `ExcelService`: Gerencia a conexão com o Google Sheets (via gspread/oauth2) e a leitura/escrita nas planilhas locais `.xlsx` usando `openpyxl`.
  - `DuplicateService`: Engine de processamento de linguagem natural (`difflib`) que escaneia a base de dados mestre em busca de registros semelhantes baseando-se em um limiar configurável (`config.py`).
  - `CrossService`: Analisa a matriz relacional (Contas a Pagar vs. Notas de Compra) e identifica falhas de integridade referencial.
  - `MigrationService`: Gere o pool de migrações confirmadas antes do salvamento final nos arquivos físicos.

## Fluxo de Processamento (Pipeline)

1. **Setup & Ingestão (Boot):**
   - O aplicativo lê o `config.py`.
   - Inicializa os serviços e conecta à API do Google Sheets.
   - Escaneia as planilhas locais nas pastas permitidas, filtrando e estruturando os arquivos mapeados.
2. **Análise Base (Varredura Combinatória):**
   - Extrai as contagens de ocorrências.
   - Cruza a base limpa da nuvem com as planilhas locais.
   - Roda o algoritmo de similaridade para criar grupos de resolução automática.
3. **Loop Interativo (Main Loop):**
   - A View é renderizada aguardando interação.
   - O Controller gerencia o estado através das seleções do usuário (Agrupar, Ignorar, Busca Manual).
4. **Resolução e Commit (Export):**
   - As tabelas são processadas na memória localmente.
   - O estado do sistema aplica o cache das trocas.
   - As planilhas modificadas são exportadas nas pastas de saída (`saida/`) e um relatório final é impresso.

## Considerações de Performance

O código foi refatorado na versão 8.0 para minimizar iterações desnecessárias. A leitura inicial cria dicionários em cache, o processamento ocorre predominantemente em estruturas nativas otimizadas do Python (Sets, Dictionaries) para tempo constante $O(1)$ nas verificações, e as planilhas `openpyxl` são salvas de uma única vez (Bulk Update).
