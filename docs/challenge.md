# Stark Bank Challenge - Requisitos de Negócio

**Versão:** 1.0  
**Data:** Fevereiro 2026  
**Autor:** Candidato Processo Seletivo Stark Bank

## 1. Contexto

Este documento descreve os requisitos de negócio para o desafio técnico do processo seletivo Stark Bank. O objetivo é desenvolver uma aplicação que automatize a emissão de faturas (invoices), processe pagamentos via webhooks e realize transferências automáticas dos valores recebidos.

### 1.1. Ambiente

- Plataforma: Stark Bank Sandbox
- Python 3.14
- FastAPI

## 2. Objetivos

### 2.1. Objetivo Principal
Desenvolver uma integração automatizada com os serviços do Stark Bank que demonstre:

- Capacidade de integração com APIs externas
- Arquitetura orientada a eventos
- Tratamento robusto de erros e retry
- Boas práticas de segurança e logging
- Monolito modular
- Não deve utilizar pydantic

### 2.2. Objetivos Específicos

- Automatizar a emissão periódica de invoices
- Processar notificações de pagamento via webhooks
- Executar transferências automáticas de valores recebidos
- Garantir rastreabilidade completa das operações
- Implementar mecanismos de resiliência e tolerância a falhas

## 3. Requisitos Funcionais

### RF001: Geração Automática de Invoices
**Descrição:** O sistema deve emitir invoices automaticamente a cada 3 horas durante 24 horas.

**Critérios de Aceitação:**

- Emitir entre 8 e 12 invoices por ciclo (quantidade aleatória)
- Gerar dados de pagadores aleatórios (nome, CPF/CNPJ, email)
- Validar CPF/CNPJ antes de criar invoice
- Executar 8 ciclos completos (24 horas / 3 horas)
- Persistir todas as invoices criadas no banco de dados
- Publicar evento InvoiceCreated para cada invoice gerada
- Continuar execução mesmo se algumas invoices falharem

**Regras de Negócio:**

- Valor da invoice: entre R$ 100,00 e R$ 1.000,00 (aleatório)
- Vencimento: 3 dias após criação
- CPF deve ter 11 dígitos e ser válido
- CNPJ deve ter 14 dígitos e ser válido

### RF002: Processamento de Webhooks de Pagamento
**Descrição:** O sistema deve receber e processar notificações de pagamento enviadas pelo Stark Bank.

**Critérios de Aceitação:**

- Endpoint público `POST /webhooks/invoice`
- Validar assinatura digital do webhook (segurança)
- Extrair dados do pagamento (invoice_id, amount, fee)
- Atualizar status da invoice no banco de dados
- Calcular valor líquido (amount - fee)
- Publicar evento InvoicePaid após processar
- Retornar HTTP 200 em caso de sucesso
- Retornar HTTP 401 se assinatura inválida
- Retornar HTTP 400 se payload malformado

**Regras de Negócio:**

- Apenas invoices com status "paid" devem acionar transferência
- Valor líquido = valor bruto - taxas do Stark Bank
- Webhook deve ser idempotente (processar duplicatas sem erro)

### RF003: Transferências Automáticas
**Descrição:** O sistema deve transferir automaticamente os valores recebidos (líquidos) para a conta do Stark Bank.

**Critérios de Aceitação:**

- Transferir valor líquido (amount - fee)
- Usar dados da conta destino especificada
- Garantir idempotência via external_id
- Persistir transferência no banco de dados
- Publicar evento TransferCompleted após sucesso
- Não duplicar transferências para mesma invoice

**Dados da Conta Destino:**

- Banco: 20018183
- Agência: 0001
- Conta: 6341320293482496
- Nome: Stark Bank S.A.
- CNPJ: 20.018.183/0001-80
- Tipo: pagamento

**Regras de Negócio:**

- `external_id = invoice-{invoice_id}` (garante idempotência)
- Transferência só deve ser criada após confirmação de pagamento
- Em caso de falha, sistema deve realizar retry automático

### RF004: Processamento de Webhooks de Transferência
**Descrição:** O sistema deve receber e processar notificações de status de transferência enviadas pelo Stark Bank.

**Critérios de Aceitação:**

- Endpoint público `POST /webhooks/transfer`
- Validar assinatura digital do webhook (segurança)
- Extrair dados da transferência (transfer_id, status, amount)
- Atualizar status da transferência no banco de dados
- Publicar evento TransferStatusUpdated após processar
- Retornar HTTP 200 em caso de sucesso
- Retornar HTTP 401 se assinatura inválida
- Retornar HTTP 400 se payload malformado

**Regras de Negócio:**

- Processar atualizações de status: processing, success, failed
- Status "success" indica transferência completada com sucesso
- Status "failed" indica falha definitiva (requer análise manual)
- Webhook deve ser idempotente (processar duplicatas sem erro)
- Registrar todas as atualizações em auditoria

### RF005: Consulta de Invoices
**Descrição:** O sistema deve expor endpoints para consulta de invoices criadas.

**Critérios de Aceitação:**

- `GET /invoices` - lista todas as invoices
- `GET /invoices/{id}` - consulta invoice específica
- Suportar filtros por status (created, paid, failed)
- Suportar paginação (limit, offset)
- Retornar dados completos da invoice
- Requer autenticação via API Key

### RF006: Consulta de Transferências
**Descrição:** O sistema deve expor endpoints para consulta de transferências realizadas.

**Critérios de Aceitação:**

- `GET /transfers` - lista todas as transferências
- `GET /transfers/{id}` - consulta transferência específica
- Suportar filtros por status (processing, success, failed)
- Suportar paginação (limit, offset)
- Retornar dados completos da transferência
- Requer autenticação via API Key

### RF007: Health Check
**Descrição:** O sistema deve expor endpoint para verificação de saúde da aplicação.

**Critérios de Aceitação:**

- `GET /health` - verifica status da aplicação
- Verificar conectividade com banco de dados
- Retornar timestamp da verificação
- Endpoint público (sem autenticação)

## 4. Requisitos Não-Funcionais

### RNF001: Confiabilidade e Resiliência
**Descrição:** O sistema deve ser resiliente a falhas temporárias da API do Stark Bank.

**Critérios de Aceitação:**

- Implementar retry automático em todas as integrações
- Estratégia de retry: 5 tentativas com backoff exponencial

  - Tentativa 1: imediata
  - Tentativa 2: após 1 minuto (60s)
  - Tentativa 3: após 2 minutos (120s)
  - Tentativa 4: após 4 minutos (240s)
  - Tentativa 5: após 8 minutos (480s)

- Fazer retry apenas em erros retriáveis (timeout, 5xx, 429)
- NÃO fazer retry em erros de validação (4xx exceto 429)
- Registrar todas as tentativas em logs
- Persistir contadores de retry no banco de dados

**Erros Retriáveis:**

- Timeout de conexão
- Erros 5xx (server error)
- Erro 429 (rate limit)
- Erros de rede (ConnectionError)

**Erros Não-Retriáveis:**

- Erros 400, 401, 403, 404, 422 (client error)
- Erros de validação de dados
- Erros de autenticação

### RNF002: Rastreabilidade e Auditoria
**Descrição:** O sistema deve manter registro completo de todas as operações.

**Critérios de Aceitação:**

- Logging estruturado (formato JSON) de todas operações
- Persistir todos os eventos na tabela `events_log`
- Logs devem incluir: timestamp, event_type, payload, metadata
- Níveis de log apropriados (INFO, WARNING, ERROR)
- Não expor dados sensíveis em logs (chaves, senhas)
- Correlacionar operações via event_id único
- Armazenar logs em arquivo e console

**Eventos Auditados:**

- invoice.created - Invoice criada
- invoice.paid - Invoice paga (via webhook)
- transfer.initiated - Transferência iniciada
- transfer.processing - Transferência em processamento (via webhook)
- transfer.completed - Transferência concluída (via webhook)
- transfer.failed - Transferência falhou (via webhook)
- operation.failed - Operação falhou após todos os retries
- error.occurred - Erro capturado

### RNF003: Segurança
**Descrição:** O sistema deve implementar controles de segurança adequados.

**Critérios de Aceitação:**

- Validar assinatura digital de todos os webhooks
- Autenticação via API Key para endpoints sensíveis
- Credenciais em variáveis de ambiente (nunca no código)
- Comparação segura de API Keys (proteção contra timing attacks)
- HTTPS obrigatório em produção
- Não expor stack traces em respostas de erro
- Rate limiting em endpoints públicos (futuro)

**Endpoints Públicos:**

- `GET /health` - Sem autenticação
- `POST /webhooks/invoice` - Validado por assinatura digital
- `POST /webhooks/transfer` - Validado por assinatura digital

**Endpoints Protegidos (requerem API Key via header X-API-Key):**

- `GET /invoices`
- `GET /invoices/{id}`
- `GET /transfers`
- `GET /transfers/{id}`
- `GET /docs` (Swagger)
- `GET /openapi.json`

### RNF004: Performance
**Critérios de Aceitação:**

- Criar invoice: < 5 segundos (sem retry)
- Processar webhook: < 2 segundos
- Criar transferência: < 5 segundos (sem retry)
- Consultar invoices/transfers: < 1 segundo
- Scheduler deve executar pontualmente a cada 3 horas

### RNF005: Escalabilidade

- Suportar criação de 96 invoices em 24 horas (8 ciclos × 12 max)
- Processar webhooks concorrentemente (se múltiplos chegarem)
- Banco de dados deve suportar crescimento de dados
- Arquitetura modular permite futura extração de microserviços

### RNF006: Manutenibilidade

- Arquitetura modular (monolito modular)
- Desacoplamento via Event Bus
- Código testável (cobertura > 85%)
- Documentação completa (negócio + arquitetura + API)
- Python 3.13 com bibliotecas atualizadas
- NÃO usar Pydantic (alinhamento com stack Stark Bank)
- Type hints em todo o código
- Linting e formatação automatizados (Ruff)

## 5. Regras de Negócio

### RN001: Geração de Dados Aleatórios

- Usar biblioteca Faker para gerar nomes realistas
- 70% de invoices com CPF (pessoa física)
- 30% de invoices com CNPJ (pessoa jurídica)
- Valores aleatórios entre R$ 100,00 e R$ 1.000,00
- Quantidade aleatória entre 8 e 12 invoices por ciclo

### RN002: Validação de Documentos

- CPF: 11 dígitos numéricos, validar dígitos verificadores
- CNPJ: 14 dígitos numéricos, validar dígitos verificadores
- Rejeitar CPF/CNPJ com todos os dígitos iguais (ex: 111.111.111-11)

### RN003: Cálculo de Valor Líquido

- valor_liquido = valor_bruto - taxas
- Taxas são informadas pelo Stark Bank no webhook
- Valor líquido nunca pode ser negativo

### RN004: Idempotência de Transferências

- Usar `external_id = invoice-{invoice_id}` em todas as transferências
- Se transferência com mesmo external_id já existe, retornar a existente
- Não criar transferências duplicadas para mesma invoice

### RN005: Estados de Invoice

Estados válidos:

- `created` - Invoice criada, aguardando pagamento
- `paid` - Invoice paga, confirmada via webhook
- `canceled` - Invoice cancelada
- `expired` - Invoice expirada 

### RN006: Estados de Transferência

Estados válidos:

- `created` - Transferência criada localmente
- `processing` - Transferência em processamento no Stark Bank
- `success` - Transferência concluída com sucesso
- `failed` - Transferência falhou definitivamente

## 6. Restrições

**Técnicas**

- Linguagem: Python 3.13 obrigatório
- Stack: Alinhada com Stark Bank (sem Pydantic)
- API: Stark Bank SDK v2.14.0+
- Banco de dados: SQLite (persistente)
- Deploy: Railway free tier

**Temporais**

- Execução: 24 horas contínuas
- Intervalo de geração: 3 horas (fixo)

**Funcionais**

- Ambiente: Stark Bank Sandbox apenas
- Conta destino: Fixa, conforme especificado
- Scheduler: Processo separado da API

## 7. Diagramas

### 7.1. Fluxo Geral do Processo

```mermaid
graph TB
    Start([Início - 00:00]) --> Scheduler[Scheduler Inicia]
    Scheduler --> Cycle{Executar<br/>Ciclo?}
    
    Cycle -->|A cada 3h| Generate[Gerar 8-12 Invoices]
    Generate --> CreateInv[Criar Invoice via<br/>Stark Bank API]
    CreateInv --> SaveInv[Salvar no Banco]
    SaveInv --> EventInv[Publicar Evento<br/>InvoiceCreated]
    EventInv --> MoreInv{Mais<br/>Invoices?}
    
    MoreInv -->|Sim| CreateInv
    MoreInv -->|Não| Wait[Aguardar 3 horas]
    Wait --> Check{24h<br/>completas?}
    
    Check -->|Não| Cycle
    Check -->|Sim| End([Fim])
    
    %% Fluxo paralelo - Webhooks de Invoice
    StarkBank[(Stark Bank<br/>Sandbox)] -.Simula<br/>Pagamento.-> Webhook[POST /webhooks/invoice]
    Webhook --> ValidateSig{Assinatura<br/>Válida?}
    ValidateSig -->|Não| Reject[HTTP 401]
    ValidateSig -->|Sim| ProcessWH[Processar Webhook]
    ProcessWH --> UpdateInv[Atualizar Invoice<br/>status=paid]
    UpdateInv --> EventPaid[Publicar Evento<br/>InvoicePaid]
    EventPaid --> ListenTransfer[Handler Escuta<br/>InvoicePaid]
    ListenTransfer --> CalcNet[Calcular Valor Líquido<br/>amount - fee]
    CalcNet --> CreateTransfer[Criar Transfer via<br/>Stark Bank API]
    CreateTransfer --> SaveTransfer[Salvar no Banco<br/>status=created]
    SaveTransfer --> EventTransfer[Publicar Evento<br/>TransferInitiated]
    EventTransfer --> Done[HTTP 200]
    
    %% Fluxo paralelo - Webhooks de Transfer
    StarkBank -.Atualização<br/>Status.-> WebhookTrf[POST /webhooks/transfer]
    WebhookTrf --> ValidateSigTrf{Assinatura<br/>Válida?}
    ValidateSigTrf -->|Não| RejectTrf[HTTP 401]
    ValidateSigTrf -->|Sim| ProcessWHTrf[Processar Webhook]
    ProcessWHTrf --> UpdateTrf[Atualizar Transfer<br/>status no Banco]
    UpdateTrf --> EventTrfStatus[Publicar Evento<br/>TransferStatus]
    EventTrfStatus --> DoneTrf[HTTP 200]
    
    style Start fill:#90EE90
    style End fill:#FFB6C1
    style StarkBank fill:#87CEEB
    style Webhook fill:#FFD700
    style WebhookTrf fill:#FFD700
    style Reject fill:#FF6B6B
    style RejectTrf fill:#FF6B6B
    style Done fill:#90EE90
    style DoneTrf fill:#90EE90
```

### 7.2. Diagrama de Sequência - Fluxo Completo

```mermaid
sequenceDiagram
    participant S as Scheduler
    participant IG as Invoice Generator
    participant SB as Stark Bank API
    participant DB as Database
    participant EB as Event Bus
    participant WH as Webhook Endpoint
    participant TH as Transfer Handler
    
    Note over S: A cada 3 horas (8x em 24h)
    
    S->>IG: Executar geração
    loop 8 a 12 vezes
        IG->>IG: Gerar dados aleatórios (Faker)
        IG->>IG: Validar CPF/CNPJ
        IG->>SB: POST /invoices (com retry)
        alt Sucesso
            SB-->>IG: Invoice criada (ID, status)
            IG->>DB: Salvar invoice
            IG->>EB: Publish InvoiceCreated
        else Falha após retries
            SB-->>IG: Erro
            IG->>DB: Salvar com status=failed
            IG->>EB: Publish OperationFailed
        end
    end
    
    Note over SB: Sandbox simula pagamento
    
    SB->>WH: POST /webhooks/invoice + Digital-Signature
    WH->>WH: Validar assinatura digital
    alt Assinatura inválida
        WH-->>SB: HTTP 401 Unauthorized
    else Assinatura válida
        WH->>WH: Parsear payload
        WH->>DB: Atualizar invoice (status=paid, fee, net_amount)
        WH->>EB: Publish InvoicePaid
        WH-->>SB: HTTP 200 OK
        
        EB->>TH: Notificar InvoicePaid
        TH->>TH: Calcular valor líquido
        TH->>DB: Verificar transferência existente
        alt Transferência já existe
            TH->>TH: Idempotência - ignorar
        else Transferência não existe
            TH->>SB: POST /transfers (com retry, external_id)
            alt Sucesso
                SB-->>TH: Transfer criada
                TH->>DB: Salvar transfer (status=created)
                TH->>EB: Publish TransferInitiated
            else Falha após retries
                SB-->>TH: Erro
                TH->>DB: Salvar transfer (status=failed)
                TH->>EB: Publish OperationFailed
            end
        end
    end
    
    Note over SB: Sandbox processa transferência
    
    SB->>WH: POST /webhooks/transfer + Digital-Signature
    WH->>WH: Validar assinatura digital
    alt Assinatura inválida
        WH-->>SB: HTTP 401 Unauthorized
    else Assinatura válida
        WH->>WH: Parsear payload
        WH->>DB: Atualizar transfer (status=processing/success/failed)
        WH->>EB: Publish TransferStatusUpdated
        WH-->>SB: HTTP 200 OK
    end
    
    Note over DB: Todas operações auditadas em events_log
```

### 7.3. Diagrama de Estados - Invoice

```mermaid
stateDiagram-v2
    [*] --> Created: Invoice criada via API
    
    Created --> Paid: Webhook recebido\n(status=paid)
    Created --> Canceled: Cancelada manualmente\n(não implementado)
    Created --> Expired: Vencimento expirado\n(não implementado)
    Created --> Failed: Erro na criação\n(após retries)
    
    Paid --> [*]: Transfer criada
    Canceled --> [*]
    Expired --> [*]
    Failed --> [*]
    
    note right of Created
        Estado inicial
        Aguardando pagamento
    end note
    
    note right of Paid
        Pagamento confirmado
        Aciona criação de transfer
    end note
```

### 7.4. Diagrama de Estados - Transfer

```mermaid
stateDiagram-v2
    [*] --> Created: Transfer criada via API\nlocalmente
    
    Created --> Processing: Webhook recebido\nstatus=processing
    Processing --> Success: Webhook recebido\nstatus=success
    Processing --> Failed: Webhook recebido\nstatus=failed
    
    Created --> Failed: Erro na criação\n(após retries)
    
    Failed --> Created: Retry manual\n(não implementado)
    
    Success --> [*]
    Failed --> [*]
    
    note right of Created
        Transferência criada localmente
        Enviada ao Stark Bank
    end note
    
    note right of Processing
        Em processamento
        Aguardando confirmação
    end note
    
    note right of Success
        Transferência confirmada
        Valor transferido com sucesso
    end note
    
    note right of Failed
        Falha permanente
        Requer intervenção manual
    end note
```

### 7.5. Arquitetura de Módulos

```mermaid
graph TB
    subgraph "Processos"
        API[API Web\nFastAPI]
        SCHED[Scheduler\nAPScheduler]
    end
    
    subgraph "Shared - Componentes Compartilhados"
        EB[Event Bus\nPub/Sub]
        DB[(SQLite\nDatabase)]
        LOG[Logger\nEstruturado]
        SEC[Security\nAPI Key Validator]
    end
    
    subgraph "Módulos de Domínio"
        INV[Invoices Module\n- Generator\n- Service\n- Events]
        WH[Webhooks Module\n- Receiver\n- Validator\n- Events]
        TRF[Transfers Module\n- Service\n- Handler\n- Events]
        SI[Stark Integration\n- Invoice API\n- Transfer API\n- Retry Logic]
    end
    
    subgraph "APIs Externas"
        SB[Stark Bank API\nSandbox]
    end
    
    SCHED --> INV
    API --> WH
    API --> SEC
    
    INV --> EB
    INV --> DB
    INV --> SI
    
    WH --> EB
    WH --> DB
    WH --> SEC
    
    TRF --> EB
    TRF --> DB
    TRF --> SI
    
    SI --> SB
    
    EB -.notifica.-> INV
    EB -.notifica.-> TRF
    EB --> DB
    
    INV --> LOG
    WH --> LOG
    TRF --> LOG
    SI --> LOG
    
    style API fill:#FFD700
    style SCHED fill:#87CEEB
    style EB fill:#90EE90
    style DB fill:#DDA0DD
    style SB fill:#FF6B6B
```

### 7.6. Fluxo de Eventos (Event Bus)

```mermaid
graph LR
    subgraph "Publishers"
        IG[Invoice Generator]
        WH[Webhook Handler]
        TS[Transfer Service]
    end
    
    subgraph "Event Bus"
        EB{Event Bus\nPub/Sub}
    end
    
    subgraph "Subscribers"
        L[Logger]
        A[Auditor]
        TH[Transfer Handler]
        M[Metrics Collector]
    end
    
    subgraph "Persistência"
        DB[(events_log)]
    end
    
    IG -->|InvoiceCreated| EB
    WH -->|InvoicePaid| EB
    WH -->|TransferStatusUpdated| EB
    TS -->|TransferInitiated| EB
    TS -->|TransferCompleted| EB
    TS -->|TransferFailed| EB
    TS -->|OperationFailed| EB
    
    EB -->|todos eventos| L
    EB -->|todos eventos| A
    EB -->|InvoicePaid| TH
    EB -->|todos eventos| M
    
    A --> DB
    
    style EB fill:#90EE90
    style DB fill:#DDA0DD
```

### 7.7. Estratégia de Retry

```mermaid
graph TB
    Start([Operação API]) --> Try1[Tentativa 1\nImediata]
    Try1 --> Check1{Sucesso?}
    Check1 -->|Sim| Success([Retornar Resultado])
    Check1 -->|Erro Retriável| Wait1[Aguardar 1 min]
    Check1 -->|Erro Não-Retriável| Fail([Lançar Exceção])
    
    Wait1 --> Try2[Tentativa 2]
    Try2 --> Check2{Sucesso?}
    Check2 -->|Sim| Success
    Check2 -->|Erro Retriável| Wait2[Aguardar 2 min]
    Check2 -->|Erro Não-Retriável| Fail
    
    Wait2 --> Try3[Tentativa 3]
    Try3 --> Check3{Sucesso?}
    Check3 -->|Sim| Success
    Check3 -->|Erro Retriável| Wait3[Aguardar 4 min]
    Check3 -->|Erro Não-Retriável| Fail
    
    Wait3 --> Try4[Tentativa 4]
    Try4 --> Check4{Sucesso?}
    Check4 -->|Sim| Success
    Check4 -->|Erro Retriável| Wait4[Aguardar 8 min]
    Check4 -->|Erro Não-Retriável| Fail
    
    Wait4 --> Try5[Tentativa 5\nÚltima]
    Try5 --> Check5{Sucesso?}
    Check5 -->|Sim| Success
    Check5 -->|Erro Qualquer| Fail
    
    style Success fill:#90EE90
    style Fail fill:#FF6B6B
    style Try1 fill:#FFD700
    style Try2 fill:#FFD700
    style Try3 fill:#FFD700
    style Try4 fill:#FFD700
    style Try5 fill:#FFA500
```

**Erros Retriáveis:**

- Timeout (ConnectionTimeout, ReadTimeout)
- HTTP 5xx (500, 502, 503, 504)
- HTTP 429 (Rate Limit)
- ConnectionError

**Erros Não-Retriáveis:**

- HTTP 4xx (400, 401, 403, 404, 422)
- ValidationError
- AuthenticationError

## 8. Modelo de Dados

### 8.1. Estrutura do Banco de Dados

```mermaid
erDiagram
    INVOICES ||--o{ TRANSFERS : "gera"
    INVOICES ||--o{ EVENTS_LOG : "registra"
    TRANSFERS ||--o{ EVENTS_LOG : "registra"
    
    INVOICES {
        uuid id PK
        string stark_invoice_id UK
        decimal amount
        string customer_name
        string customer_tax_id
        string customer_email
        enum status
        timestamp created_at
        timestamp paid_at
        decimal fee
        decimal net_amount
        int retry_count
        timestamp last_retry_at
        text error_message
    }
    
    TRANSFERS {
        uuid id PK
        uuid invoice_id FK
        string stark_transfer_id UK
        string external_id UK
        decimal amount
        enum status
        timestamp created_at
        timestamp updated_at
        timestamp completed_at
        int retry_count
        timestamp last_retry_at
        text error_message
    }
    
    EVENTS_LOG {
        int id PK
        uuid event_id UK
        string event_type
        json payload
        json metadata
        timestamp timestamp
        boolean processed
    }
```

## 9. Critérios de Aceite do Projeto

### 9.1. Funcionalidade

- Sistema gera 8-12 invoices a cada 3 horas
- Sistema executa por 24 horas (8 ciclos completos)
- Webhook de invoice processa pagamentos corretamente
- Webhook de transfer processa atualizações de status corretamente
- Transferências são criadas automaticamente
- Valor líquido calculado corretamente (amount - fee)
- Dados transferidos para conta Stark Bank especificada
- Status de transferências atualizado via webhook
- Endpoints de consulta funcionam corretamente

### 9.2. Qualidade

- Cobertura de testes > 85%
- Todos comportamentos testados
- Retry funciona conforme especificado
- Idempotência de transferências validada
- Validação de CPF/CNPJ implementada
- API Key protege endpoints corretamente

### 9.3. Documentação

- Documento de arquitetura completo
- Documento de especificação da API
- README com instruções de execução
- Diagramas incluídos na documentação
- Código comentado onde necessário

### 9.4. Entrega

- Código no repositório GitHub público
- Aplicação deployada no Railway
- Executando por 24 horas
- Logs e evidências de execução
- Todas dependências documentadas

## 10. Glossário

- Invoice: Fatura/cobrança gerada para um cliente
- Transfer: Transferência bancária para conta destino
- Webhook: Notificação HTTP enviada por evento externo
- Event Bus: Sistema de mensageria pub/sub para desacoplamento
- Retry: Tentativa automática após falha
- Backoff Exponencial: Estratégia de espera crescente entre retries
- Idempotência: Propriedade de operação produzir mesmo resultado se executada múltiplas vezes
- External ID: Identificador externo para garantir idempotência
- API Key: Chave de autenticação para acesso a API
- CPF: Cadastro de Pessoa Física (11 dígitos)
- CNPJ: Cadastro Nacional de Pessoa Jurídica (14 dígitos)
- Sandbox: Ambiente de testes que simula produção
- DTO: Data Transfer Object - objeto para transferência de dados
- Valor Líquido: Valor bruto menos taxas

## 11. Referências

- Stark Bank API Documentation ()
- Stark Bank Python SDK
- FastAPI Documentation
- Python 3.14 Release Notes
- Railway Documentation
