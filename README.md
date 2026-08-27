# DataMergeTool

![Python](https://img.shields.io/badge/Python-3.x-blue)![Google Sheets API](https://img.shields.io/badge/Google%20Sheets-API-green)![Openpyxl](https://img.shields.io/badge/Openpyxl-Excel-lightgrey)![Status](https://img.shields.io/badge/Status-Production-success)
![License](https://img.shields.io/badge/License-MIT-blue)

> Ferramenta de **Saneamento de Dados**, **Desduplicação Inteligente** e **Auditoria de Integridade Referencial** integrando bases na nuvem (Google Sheets) com planilhas de movimentação locais (.xlsx).

---

## Problema e Solução

Em operações financeiras e de infraestrutura, é comum que sistemas descentralizados gerem um acúmulo de dados sujos. Entidades (como _Fornecedores_ ou _Produtos_) acabam sendo cadastradas repetidas vezes com leves variações no nome ou erros de digitação. Isso quebra o vínculo entre diferentes relatórios (como _Contas a Pagar_ e _Notas de Compra_).

A ferramenta atua como um hub central que lê a **Base Oficial (Nuvem)**, varre todas as **Planilhas Locais**, localiza duplicações usando um algoritmo de similaridade textual e cruza tabelas relacionais em busca de chaves quebradas. Tudo isso orquestrado por uma interface de terminal altamente interativa que permite realizar _batch migrations_ de dados em lote de forma limpa e segura.

_Projeto desenvolvido com base em uma demanda real e generalizado para adoção por qualquer empresa._

---

## Tecnologias

- **Python 3** (Linguagem Principal)
- **Openpyxl** (Manipulação e atualização massiva de arquivos Excel `.xlsx`)
- **Gspread / google-auth** (Comunicação com a API do Google Sheets)
- **Rich** (Renderização avançada de Interface Gráfica e Menus Interativos no Terminal)
- **Difflib / SequenceMatcher** (Engine nativa de NLP para similaridade e agrupamento)

---

## Arquitetura Híbrida

O DataMergeTool opera com uma arquitetura **MVC** (Model-View-Controller) orientada a processamento em memória, evitando corromper arquivos durante a manipulação:

```text
 ┌───────────────────────┐            ┌─────────────────────────┐
 │ Cloud (Google Sheets) │            │  Local System (.xlsx)   │
 │   (Source of Truth)   │            │(Daily Transaction Files)│
 └───────────┬───────────┘            └────────────┬────────────┘
             │                                     │
             │           DataMergeTool             │
             ▼                                     ▼
        [ API Rest ]                          [ Openpyxl ]
             │                                     │
             └──────────────────┬──────────────────┘
                                ▼
                       Engine de Similaridade
                        Validação Relacional
                                │
                                ▼
                      Interactive UI (Rich)
                       (Resolução Interativa)
                                │
                                ▼
                       [ State & History ] (Auto-save)
                                │
                                ▼
                         Bulk Export (Saída)
                      (Planilhas Higienizadas)
```

---

## Fluxo de Funcionamento

1. **Setup Agnóstico:** O sistema carrega as regras e abas do arquivo `config.py`.
2. **Ingestão Híbrida:** Download da base oficial via API Google Sheets e varredura combinatória estruturada das planilhas locais (Excel).
3. **Análise de Dados:** Algoritmos identificam entidades duplicadas, órfãos e falhas referenciais.
4. **Interação do Usuário:** O usuário decide, através do terminal UI, aprovar ou não as migrações e correções através de um menu interativo rico.
5. **Aplicação em Memória:** As modificações ficam salvas no sistema de histórico (permitindo rollback e desfazer via `Ctrl+Z`).
6. **Deploy / Export:** Quando concluído, o sistema efetua o salvamento em lote gerando novos arquivos seguros e um log contendo orientações de exclusão para a nuvem.

---

## Funcionalidades

- **Resolução Automática:** Identificação de nomes semelhantes e agrupamento fuzzy configurável (ex: _Fornecedor SA_ vs _Fornecedor S/A_).
- **Substituição Manual (De ➔ Para):** Força transições de IDs antigos para novos IDs centralizados com cálculo imediato de impacto em todas as planilhas.
- **Sincronização Referencial:** Cruza chaves estrangeiras entre relatórios (ex: Contas a Pagar x Notas de Compra) verificando se a mesma nota pontua para a mesma entidade.
- **Auditorias Dinâmicas (Raio-X):** Caçador de IDs Órfãos (Inexistentes na nuvem) e Registros Inativos (Que nunca pontuaram movimentações físicas).
- **Histórico e Rollback (Ctrl+Z):** Ações guardadas em cache serializável. Cometeu um erro? Aperte `Z` e reverta transações na mesma hora.

---

## Como Usar e Documentação

Para aprofundar-se na arquitetura do código ou entender os manuais de utilização corporativa, consulte a nossa biblioteca de documentações dedicada:

- 📘 **[Guia de Uso (USER_GUIDE)](USER_GUIDE.md):** Manual completo de operação da interface de usuário, passos de configuração (`config.py`) para sua empresa e explicação de valor de negócio de cada módulo.
- 📙 **[Referência da Arquitetura (ARCHITECTURE)](ARCHITECTURE.md):** Design patterns utilizados (MVC), tomada de decisões em performance e fluxo de _Pipelines_.
- 📗 **[Referência da API (API_REFERENCE)](API_REFERENCE.md):** Um dicionário completo listando todos os métodos internos, classes base e módulos que estruturam o código fonte da ferramenta.

---

## Esclarecendo Dúvidas Frequentes

**O DataMergeTool vai alterar minhas planilhas originais e causar corrupção?**
Não. Toda a engenharia da ferramenta processa as substituições em memória (RAM) e possui um controlador de estado. Os dados só são gravados em arquivos físicos ao final (tecla E), e mesmo assim, eles são injetados em planilhas completamente novas e exportadas numa pasta isolada (`/saida/`), preservando seus dados cruciais intactos.

**Esse software só funciona para Controle de Fornecedores e Notas Fiscais?**
A arquitetura foi inteiramente **generalizada**. Hoje, todos os nomes de abas, entidades, colunas e parâmetros não estão presos no código-fonte, eles derivam do arquivo `config.py`. Seja unificando centros de custos, catálogo de produtos, matrículas de alunos ou qualquer outra entidade empresarial híbrida, o DataMergeTool suportará a demanda após 5 minutos de parametrização.

**E se o software fechar do nada após eu arrumar 50 IDs duplicados? Perco o progresso?**
Não. O `StateManager` garante o serializamento JSON de sua sessão a cada movimento. Ao reabrir o script, ele retomará exatamente de onde você parou, restaurando sua fila de pendências e preservando as planilhas em segurança.

---

## Conceitos Aplicados

- **Model-View-Controller (MVC)**
- **Separação de Preocupações (Separation of Concerns)**
- **Engenharia Híbrida (Cloud Integration + File I/O System)**
- **NLP de Baixo Nível** (Algoritmos Combinatórios de Similaridade Lexical)
- **Processamento em Memória e Estruturas O(1)** (Dictionaries, HashSets)
- **Gerenciamento de Estado e Serialização Persistente**

---

## Estrutura do Projeto

```text
DataMergeTool/
├── main.py                     (Entrypoint da aplicação)
├── config.py                   (Configurações dinâmicas e agnósticas da empresa)
├── requirements.txt            (Dependências PIP)
├── credentials.json            (Token Google Cloud - a ser fornecido localmente)
├── /models/
│   ├── entity.py               (Estruturas base de dados)
│   ├── duplicate_group.py
│   └── migration.py            (Histórico de transições/Rollbacks)
├── /services/
│   ├── excel_service.py        (I/O, Gspread e Openpyxl)
│   ├── duplicate_service.py    (Lógica NLP e Identificação Fuzzy)
│   ├── cross_service.py        (Análise Referencial e Auditorias)
│   ├── migration_service.py
│   └── report_service.py
├── /core/
│   └── state_manager.py        (Controlador de Sessão e Cache/Undo)
├── /ui/
│   └── views.py                (Engine gráfica Rich interativa)
└── /utils/
    ├── button_handlers.py      (Eventos baseados em Input de teclado)
    └── console.py              (Output Helper)
```

---

## Resultados

Originalmente, este projeto nasceu de uma dor extrema e mitigou mais de **20.000 inconsistências cadastrais** num cenário legado (sem padronização prévia de ERP) em sua primeira versão, permitindo relatórios analíticos perfeitos e migrações sistêmicas ágeis. Atualmente atinge a **versão 8.0**, completamente madura, componentizada para fins _Open-Source_ e preparada para escalar.

## Possíveis Melhorias Futuras

- Integração total de exportação na nuvem (Sobrescrever a própria nuvem via API).
- Suporte a `Pandas/Polars` para lidar com planilhas e volumes ultra-pesados (milhões de linhas).
- Implementação de CLI Arguments para operação headless via agendamento cron (Ex: `--auto-resolve`).

---

## Licença

Projeto publicado apenas para fins educacionais e de demonstração arquitetural de engenharia de software sob licença **MIT**. Informações confidenciais, chaves privadas e dados corporativos da solução original foram inteiramente desacoplados e removidos do código-fonte.
