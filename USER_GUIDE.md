# Guia do Usuário - DataMergeTool v8.0

Seja bem-vindo ao manual de operações do **DataMergeTool**. Esta aplicação foi desenvolvida de forma agnóstica para ajudar analistas de dados, auditores financeiros e gerentes de infraestrutura de **qualquer empresa** a limpar, unificar e auditar bancos de dados baseados em planilhas Excel integrados a nuvem (Google Sheets).

O objetivo principal desta ferramenta é resolver **divergências de IDs de entidades** (sejam Fornecedores, Produtos, Clientes, ou Centros de Custo), unificando nomenclaturas duplicadas e garantindo que os relatórios sejam precisos. Toda a configuração da estrutura de planilhas é ditada pelo arquivo `config.py`.

---

## 1. Preparação do Ambiente

Antes de iniciar o software, assegure-se de que:
1. **Credenciais da Nuvem:** O arquivo `credentials.json` deve estar localizado na pasta raiz do projeto. Ele contém as chaves para que a ferramenta leia a sua base Mestre oficial no Google Sheets.
2. **Configuração (`config.py`):** Edite o arquivo `config.py` para apontar para o URL da sua planilha na nuvem (`MASTER_SPREADSHEET_URL`), bem como os nomes das abas, palavras-chave e colunas específicas que sua empresa utiliza.
3. **Planilhas Locais:** As planilhas físicas contendo as movimentações (.xlsx) devem estar presentes em qualquer subpasta (ou na raiz). O sistema fará a varredura automaticamente, ignorando arquivos configurados na exclusão.
4. **Dependências:** Execute `pip install -r requirements.txt`.

Para rodar a aplicação, abra o terminal na pasta raiz e execute:
`python main.py`

---

## 2. Início: Seleção do Modo de Operação

Logo ao abrir, você verá um menu solicitando o escopo de trabalho, cujos nomes refletem o que você configurou no `config.py` (por padrão, Modo 1 e Modo 2).
* O comportamento do programa irá se adaptar dependendo de qual entidade você decidir tratar na sessão atual. 
* O sistema lerá os dados da Nuvem de acordo com as colunas-alvo definidas e fará o *caching* das transações encontradas nas suas planilhas físicas instantaneamente.

---

## 3. O Hub Principal (Menu de Operações)

Após o carregamento inicial, você será direcionado ao Hub Principal.

### Opção 1: Resolução Automática
O módulo mais poderoso do software. O sistema possui uma engine de similaridade que agrupa itens com nomes muito parecidos e recomenda automaticamente um **ID Oficial**.
Ao entrar na resolução automática:
* Selecione (apertando `ENTER`) quais IDs Antigos devem ser convertidos no ID Oficial exibido na tela.
* Após selecionar, aperte `S` para confirmar a substituição ou `P` para pular e não substituir nada.

### Opção 2: Substituição Manual
Ideal caso você saiba de antemão que dois IDs totalmente diferentes se tratam da mesma entidade.
1. Digite o nome/ID **Antigo** (Origem).
2. O sistema te pedirá o **Novo** ID Oficial (Destino).
3. Após revisão de impacto (quantidade de linhas a serem afetadas), confirme a conversão.

### Opção 3: Pesquisar Registro (Raio-X Dinâmico)
Mecanismo de consulta nativa (*Read-Only*). Use-o para rastrear a presença física de um ID nas planilhas.
* A consulta te mostrará **exatamente** em qual Arquivo, qual Aba, e qual Coluna foram encontradas ocorrências.

### Opção 4: Auditoria de Registros Órfãos
O Caçador de Anomalias. Verifica se as suas planilhas de movimentações contêm IDs lançados que **não existem** na Base Mestre hospedada no Google Sheets.

### Opção 5: Remoção de Registros Inativos
A ferramenta analisa a Base Mestre (Nuvem) e aponta os itens que têm 0 movimentações nas planilhas (cadastros mortos/inativos).

### Opção 6: Sincronização de Integridade Referencial
Voltada à conciliação entre duas áreas (ex: Contas a Pagar vs Notas). Cruza chaves primárias e estrangeiras lógicas das abas configuradas no `config.py` (`CROSS_BILLS_SHEET_KEYWORDS` e `CROSS_INVOICES_SHEET_KEYWORDS`).
* Se houver quebra (divergência entre um documento e outro), a tela de resolução permite a você sobreescrever e forçar o ID correto de um dos lados, consertando as duas pontas.

---

## 4. O Sistema de Persistência e Atualização

### Desfazer Ações (`Z`)
Cometeu um erro na Substituição? Basta utilizar `Z` no Hub para reverter a última ação e retornar tudo à origem instantaneamente. O estado é salvo em um arquivo JSON local automaticamente para cada modo.

### Exportar e Finalizar (`E`)
O trabalho feito no software **não altera** as planilhas imediatamente, funcionando com um cache em memória RAM.
* Quando concluir, tecle `E`.
* A ferramenta fará uma gravação em Lote (Bulk Update) injetando e corrigindo os dados. 
* Os arquivos corrigidos serão salvos inteiramente na pasta de segurança `/saida/`.
* O sistema gerará um `RELATORIO_EXCLUSAO.txt` com as recomendações do que deve ser apagado fisicamente da Nuvem.

### Salvar e Sair (`Q`)
Caso precise encerrar o trabalho para continuar depois, aperte `Q`. O sistema garante a integridade do JSON de backup e ao abrir novamente a sessão é retomada.
