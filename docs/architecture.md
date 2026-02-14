# Stark Bank Challenge - Documento de Arquitetura

**Versão:** 1.0  
**Data:** Fevereiro 2026  
**Autor:** Candidato Processo Seletivo Stark Bank

## 1. Visão Geral

### 1.1. Objetivo do Sistema

O sistema implementa uma integração automatizada com a plataforma Stark Bank para:

- **Gerar invoices automaticamente** a cada 3 horas durante 24 horas
- **Processar notificações de pagamento** via webhooks
- **Executar transferências automáticas** dos valores recebidos

### 1.2. Princípios Arquiteturais

#### Monolito Modular
- Aplicação única com módulos bem definidos e desacoplados
- Preparada para evolução futura para microserviços
- Comunicação inter-módulos via Event Bus

#### Event-Driven Architecture
- Desacoplamento via publicação/assinatura de eventos
- Rastreabilidade completa de operações
- Facilita auditoria e debugging

#### Resiliência por Design
- Retry automático com backoff exponencial
- Tratamento explícito de falhas
- Graceful degradation

#### Security First
- Validação de assinaturas digitais
- Autenticação via API Key
- Princípio do menor privilégio

### 1.3. Stack Tecnológico

| Componente | Tecnologia | Versão | Justificativa |
|------------|-----------|---------|---------------|
| Linguagem | Python | 3.14 | Requisito do projeto |
| Web Framework | FastAPI | 0.115+ | Performance, async, OpenAPI nativo |
| Banco de Dados | SQLite | 3.x | Simplicidade, portabilidade, sem setup |
| HTTP Client | httpx | 0.28+ | Async nativo, retry built-in |
| Scheduler | APScheduler | 3.10+ | Cron jobs em processo |
| Stark Bank SDK | starkbank | 2.14+ | SDK oficial |
| Validação | validate-docbr | 1.10+ | Validação CPF/CNPJ |
| Faker | Faker | 33+ | Geração de dados fake |
| Linting | Ruff | 0.8+ | Linting e formatação rápida |
| Testing | pytest | 8.3+ | Framework de testes padrão |

**Nota:** Pydantic não é utilizado (alinhamento com stack Stark Bank).

## 2. Arquitetura de Alto Nível

### 2.1. Visão Geral dos Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                     STARK BANK CHALLENGE                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐              ┌──────────────┐              │
│  │   FastAPI   │◄────────────►│  Scheduler   │              │
│  │  Web Server │              │ (APScheduler)│              │
│  └──────┬──────┘              └──────┬───────┘              │
│         │                             │                       │
│         │         ┌──────────────────┘                       │
│         │         │                                           │
│         ▼         ▼                                           │
│  ┌─────────────────────────────────────────┐                │
│  │          DOMAIN MODULES                  │                │
│  ├──────────────┬──────────────┬───────────┤                │
│  │   Invoices   │  Webhooks    │ Transfers │                │
│  │   Module     │   Module     │  Module   │                │
│  └──────┬───────┴──────┬───────┴─────┬─────┘                │
│         │              │             │                       │
│         └──────────────┼─────────────┘                       │
│                        ▼                                      │
│         ┌─────────────────────────────┐                      │
│         │    SHARED COMPONENTS         │                      │
│         ├────────────┬────────────────┤                      │
│         │ Event Bus  │ Stark Bank API │                      │
│         │  Logger    │   Security     │                      │
│         │ Database   │   Retry Logic  │                      │
│         └────────────┴────────────────┘                      │
│                        │                                      │
└────────────────────────┼──────────────────────────────────────┘
                         ▼
              ┌──────────────────┐
              │  Stark Bank API   │
              │    (Sandbox)      │
              └──────────────────┘
```

### 2.2. Processos do Sistema

#### Processo 1: API Web (FastAPI)
- **Porta:** 8000
- **Responsabilidade:** Expor endpoints REST e processar webhooks
- **Endpoints:**
  - `POST /webhooks/invoice` - Recebe notificações de pagamento de invoices
  - `POST /webhooks/transfer` - Recebe notificações de status de transferências
  - `GET /invoices` - Lista invoices
  - `GET /invoices/{id}` - Consulta invoice específica
  - `GET /transfers` - Lista transferências
  - `GET /transfers/{id}` - Consulta transferência específica
  - `GET /health` - Health check
  - `GET /docs` - Swagger UI

#### Processo 2: Scheduler (Background)
- **Responsabilidade:** Executar geração de invoices periodicamente
- **Schedule:** A cada 3 horas
- **Duração:** 24 horas (8 ciclos)
- **Execução:**
  - Roda em thread separada
  - Não bloqueia a API
  - Pode ser extraído para processo independente no futuro

## 3. Arquitetura Modular

### 3.1. Estrutura de Diretórios

```
stark-bank-challenge/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Entry point FastAPI
│   ├── scheduler.py               # Entry point Scheduler
│   │
│   ├── modules/                   # Domain Modules
│   │   ├── __init__.py
│   │   │
│   │   ├── invoices/              # Invoice Module
│   │   │   ├── __init__.py
│   │   │   ├── generator.py      # Geração de invoices
│   │   │   ├── service.py        # Lógica de negócio
│   │   │   ├── repository.py     # Acesso ao banco
│   │   │   ├── models.py         # Modelos de dados
│   │   │   ├── events.py         # Definição de eventos
│   │   │   └── api.py            # Endpoints REST
│   │   │
│   │   ├── webhooks/              # Webhook Module
│   │   │   ├── __init__.py
│   │   │   ├── receiver.py       # Recebe webhooks
│   │   │   ├── validator.py      # Valida assinaturas
│   │   │   ├── invoice_processor.py  # Processa webhooks de invoice
│   │   │   ├── transfer_processor.py # Processa webhooks de transfer
│   │   │   ├── events.py         # Definição de eventos
│   │   │   └── api.py            # Endpoints REST
│   │   │
│   │   └── transfers/             # Transfer Module
│   │       ├── __init__.py
│   │       ├── service.py         # Lógica de negócio
│   │       ├── handler.py         # Event handler
│   │       ├── repository.py      # Acesso ao banco
│   │       ├── models.py          # Modelos de dados
│   │       ├── events.py          # Definição de eventos
│   │       └── api.py             # Endpoints REST
│   │
│   ├── shared/                    # Shared Components
│   │   ├── __init__.py
│   │   │
│   │   ├── database/              # Database Layer
│   │   │   ├── __init__.py
│   │   │   ├── connection.py     # Connection pool
│   │   │   ├── migrations.py     # Schema migrations
│   │   │   └── base_repository.py # Base class
│   │   │
│   │   ├── events/                # Event Bus
│   │   │   ├── __init__.py
│   │   │   ├── bus.py            # Event bus implementation
│   │   │   ├── types.py          # Event types
│   │   │   └── logger.py         # Event logger
│   │   │
│   │   ├── stark/                 # Stark Bank Integration
│   │   │   ├── __init__.py
│   │   │   ├── client.py         # Cliente base
│   │   │   ├── invoice_api.py    # Invoice API
│   │   │   ├── transfer_api.py   # Transfer API
│   │   │   └── retry.py          # Retry logic
│   │   │
│   │   ├── security/              # Security
│   │   │   ├── __init__.py
│   │   │   ├── api_key.py        # API Key validator
│   │   │   ├── signature.py      # Webhook signature
│   │   │   └── constants.py      # Security constants
│   │   │
│   │   └── utils/                 # Utilities
│   │       ├── __init__.py
│   │       ├── logger.py          # Structured logger
│   │       ├── validators.py     # CPF/CNPJ validators
│   │       ├── data_generator.py # Faker wrapper
│   │       └── errors.py          # Custom exceptions
│   │
│   └── config/                    # Configuration
│       ├── __init__.py
│       ├── settings.py            # App settings
│       └── constants.py           # Business constants
│
├── tests/                         # Tests
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   └── e2e/                      # End-to-end tests
│
├── docs/                          # Documentation
│   ├── challenge.md              # Business requirements
│   ├── architecture.md           # This document
│   └── api.md                    # API specification
│
├── migrations/                    # Database migrations
│   └── 001_initial_schema.sql
│
├── .env.example                   # Environment template
├── .gitignore
├── pyproject.toml                # Dependencies (Poetry/Rye)
├── Procfile                      # Railway deployment
└── README.md                     # Setup instructions
```

### 3.2. Módulos de Domínio

#### 3.2.1. Invoices Module

**Responsabilidades:**
- Gerar invoices com dados aleatórios
- Validar CPF/CNPJ
- Criar invoices via Stark Bank API
- Persistir invoices no banco de dados
- Publicar eventos de criação
- Expor endpoints de consulta

**Componentes:**
- `InvoiceGenerator`: Gera dados e cria invoices
- `InvoiceService`: Lógica de negócio
- `InvoiceRepository`: Persistência
- `InvoiceAPI`: Endpoints REST

**Eventos Publicados:**
- `InvoiceCreated`: Invoice criada com sucesso
- `InvoiceCreationFailed`: Falha na criação

#### 3.2.2. Webhooks Module

**Responsabilidades:**
- Receber webhooks do Stark Bank (invoices e transfers)
- Validar assinatura digital
- Processar payload de pagamento de invoices
- Processar payload de status de transferências
- Atualizar status de invoices e transfers
- Publicar eventos de pagamento e transferência

**Componentes:**
- `WebhookReceiver`: Endpoints HTTP
- `SignatureValidator`: Validação de assinatura
- `InvoiceWebhookProcessor`: Processamento de invoices
- `TransferWebhookProcessor`: Processamento de transfers

**Eventos Publicados:**
- `InvoicePaid`: Invoice paga confirmada
- `TransferProcessing`: Transferência em processamento
- `TransferCompleted`: Transferência concluída com sucesso
- `TransferFailed`: Transferência falhou
- `WebhookValidationFailed`: Assinatura inválida

#### 3.2.3. Transfers Module

**Responsabilidades:**
- Escutar eventos `InvoicePaid`
- Calcular valor líquido (amount - fee)
- Criar transferências via Stark Bank API
- Garantir idempotência
- Persistir transferências
- Expor endpoints de consulta

**Componentes:**
- `TransferService`: Lógica de negócio
- `TransferHandler`: Event handler (InvoicePaid)
- `TransferRepository`: Persistência
- `TransferAPI`: Endpoints REST

**Eventos Publicados:**
- `TransferCompleted`: Transferência concluída
- `TransferFailed`: Falha na transferência

### 3.3. Componentes Compartilhados

#### 3.3.1. Event Bus

**Implementação:**
- Pattern: Pub/Sub in-memory
- Sincrono (para simplicidade)
- Handlers registrados na inicialização

**Interface:**
```python
class EventBus:
    def publish(self, event_type: str, payload: dict) -> None:
        """Publica evento para todos os subscribers"""
        
    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Registra handler para tipo de evento"""
        
    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Remove handler"""
```

**Eventos do Sistema:**
- `invoice.created` - Invoice criada
- `invoice.paid` - Invoice paga
- `transfer.initiated` - Transferência iniciada
- `transfer.processing` - Transferência em processamento
- `transfer.completed` - Transferência concluída com sucesso
- `transfer.failed` - Transferência falhou
- `operation.failed` - Operação falhou

**Persistência:**
- Todos eventos são salvos em `events_log` para auditoria

#### 3.3.2. Database Layer

**Tecnologia:** SQLite
- Arquivo: `stark_bank.db`
- Modo: WAL (Write-Ahead Logging) para concorrência
- Connection pool: sqlite3 nativo

**Tabelas:**
```sql
-- Invoices
CREATE TABLE invoices (
    id TEXT PRIMARY KEY,
    stark_invoice_id TEXT UNIQUE,
    amount REAL NOT NULL,
    customer_name TEXT NOT NULL,
    customer_tax_id TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    paid_at TEXT,
    fee REAL,
    net_amount REAL,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TEXT,
    error_message TEXT
);

-- Transfers
CREATE TABLE transfers (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    stark_transfer_id TEXT UNIQUE,
    external_id TEXT UNIQUE,
    amount REAL NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    completed_at TEXT,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TEXT,
    error_message TEXT,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

-- Events Log (auditoria)
CREATE TABLE events_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    metadata TEXT,
    timestamp TEXT NOT NULL,
    processed INTEGER DEFAULT 0
);

-- Indexes
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_stark_id ON invoices(stark_invoice_id);
CREATE INDEX idx_transfers_invoice ON transfers(invoice_id);
CREATE INDEX idx_transfers_external_id ON transfers(external_id);
CREATE INDEX idx_events_type ON events_log(event_type);
CREATE INDEX idx_events_timestamp ON events_log(timestamp);
```

#### 3.3.3. Stark Bank Integration

**Wrapper sobre SDK oficial:**
- Abstração para facilitar testes
- Retry automático com backoff exponencial
- Logging estruturado de todas operações

**Invoice API:**
```python
class StarkInvoiceAPI:
    def create_invoice(
        self,
        amount: int,
        tax_id: str,
        name: str,
        due_date: datetime
    ) -> InvoiceResponse:
        """Cria invoice no Stark Bank com retry"""
```

**Transfer API:**
```python
class StarkTransferAPI:
    def create_transfer(
        self,
        amount: int,
        external_id: str,
        bank_code: str,
        branch_code: str,
        account_number: str,
        account_type: str,
        tax_id: str,
        name: str
    ) -> TransferResponse:
        """Cria transferência no Stark Bank com retry"""
```

**Retry Strategy:**
```python
@retry(
    max_attempts=5,
    delays=[0, 60, 120, 240, 480],  # segundos
    retriable_exceptions=[TimeoutError, RateLimitError, ServerError],
    non_retriable_exceptions=[ValidationError, AuthError]
)
def _call_api(self, ...):
    """Executa chamada com retry automático"""
```

#### 3.3.4. Security Layer

**API Key Authentication:**
```python
async def verify_api_key(api_key: str = Header(..., alias="X-API-Key")):
    """Valida API Key de forma segura (constant-time comparison)"""
    if not secrets.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(status_code=401)
```

**Webhook Signature Validation:**
```python
def validate_webhook_signature(
    payload: bytes,
    signature: str,
    public_key: str
) -> bool:
    """Valida assinatura digital do webhook usando ECDSA"""
```

**Endpoints Protegidos:**
- `GET /invoices*` - Requer API Key
- `GET /transfers*` - Requer API Key
- `GET /docs` - Requer API Key

**Endpoints Públicos:**
- `GET /health` - Sem autenticação
- `POST /webhooks/invoice` - Validado por assinatura digital
- `POST /webhooks/transfer` - Validado por assinatura digital

#### 3.3.5. Logger

**Formato:** JSON estruturado
```json
{
    "timestamp": "2026-02-14T10:30:00.123Z",
    "level": "INFO",
    "module": "invoices.generator",
    "event": "invoice_created",
    "message": "Invoice created successfully",
    "data": {
        "invoice_id": "uuid-123",
        "amount": 500.00,
        "customer_tax_id": "123.456.789-00"
    },
    "correlation_id": "req-uuid-456"
}
```

**Níveis:**
- `DEBUG`: Detalhes de desenvolvimento
- `INFO`: Operações normais
- `WARNING`: Situações inesperadas não-críticas
- `ERROR`: Falhas que requerem atenção

**Saídas:**
- Console (stdout)
- Arquivo: `logs/app.log` (rotação diária)

## 4. Padrões de Design

### 4.1. Repository Pattern

Abstrai acesso ao banco de dados, facilitando testes e manutenção.

```python
class InvoiceRepository:
    def create(self, invoice: InvoiceModel) -> None:
        """Insere invoice no banco"""
        
    def get_by_id(self, invoice_id: str) -> Optional[InvoiceModel]:
        """Busca invoice por ID"""
        
    def get_by_stark_id(self, stark_id: str) -> Optional[InvoiceModel]:
        """Busca invoice por Stark ID"""
        
    def update(self, invoice: InvoiceModel) -> None:
        """Atualiza invoice"""
        
    def list(self, status: Optional[str], limit: int, offset: int) -> List[InvoiceModel]:
        """Lista invoices com filtros"""
```

### 4.2. Service Layer

Encapsula lógica de negócio, orquestrando repositórios e APIs externas.

```python
class InvoiceService:
    def __init__(
        self,
        repository: InvoiceRepository,
        stark_api: StarkInvoiceAPI,
        event_bus: EventBus
    ):
        self.repository = repository
        self.stark_api = stark_api
        self.event_bus = event_bus
        
    def create_invoice(self, data: dict) -> InvoiceModel:
        """Cria invoice com lógica de negócio completa"""
        # 1. Validar dados
        # 2. Criar no Stark Bank
        # 3. Salvar no banco
        # 4. Publicar evento
        # 5. Retornar modelo
```

### 4.3. Event-Driven Pattern

Desacoplamento entre módulos via eventos.

```python
# Publisher (Invoice Generator)
invoice = service.create_invoice(data)
event_bus.publish("invoice.created", {
    "invoice_id": invoice.id,
    "amount": invoice.amount,
    "created_at": invoice.created_at
})

# Subscriber (Transfer Handler)
event_bus.subscribe("invoice.paid", transfer_handler.handle_invoice_paid)
```

### 4.4. Dependency Injection

Facilita testes e flexibilidade.

```python
# Di container (simplificado)
def get_invoice_service() -> InvoiceService:
    """Factory function para InvoiceService"""
    db = get_database()
    repository = InvoiceRepository(db)
    stark_api = StarkInvoiceAPI()
    event_bus = get_event_bus()
    return InvoiceService(repository, stark_api, event_bus)

# Usage
@router.post("/invoices")
def create_invoice(
    data: dict,
    service: InvoiceService = Depends(get_invoice_service)
):
    return service.create_invoice(data)
```

### 4.5. Retry Pattern

Resiliência automática com backoff exponencial.

```python
def retry_with_backoff(
    func: Callable,
    max_attempts: int = 5,
    delays: List[int] = [0, 60, 120, 240, 480]
) -> Any:
    """
    Executa função com retry automático
    
    Args:
        func: Função a ser executada
        max_attempts: Número máximo de tentativas
        delays: Lista de delays em segundos entre tentativas
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except RetriableError as e:
            if attempt == max_attempts:
                raise
            delay = delays[attempt - 1]
            logger.warning(f"Attempt {attempt} failed, retrying in {delay}s")
            time.sleep(delay)
        except NonRetriableError:
            raise  # Não tenta novamente
```

### 4.6. Factory Pattern

Criação de objetos complexos.

```python
class InvoiceFactory:
    @staticmethod
    def create_random_invoice() -> dict:
        """Cria dados de invoice aleatórios"""
        faker = Faker('pt_BR')
        
        # 30% CPF, 70% CNPJ
        is_cpf = random.random() < 0.7
        
        if is_cpf:
            tax_id = generate_valid_cpf()
            name = faker.name()
        else:
            tax_id = generate_valid_cnpj()
            name = faker.company()
            
        return {
            "amount": random.randint(10000, 100000),  # centavos
            "tax_id": tax_id,
            "name": name,
            "email": faker.email(),
            "due_date": datetime.now() + timedelta(days=3)
        }
```

## 5. Fluxos de Dados

### 5.1. Fluxo de Criação de Invoice

```
1. Scheduler aciona InvoiceGenerator (a cada 3h)
2. InvoiceGenerator:
   a. Gera dados aleatórios (8-12 invoices)
   b. Valida CPF/CNPJ
3. InvoiceService:
   a. Cria invoice via StarkInvoiceAPI (com retry)
   b. Salva no banco via InvoiceRepository
   c. Publica evento "invoice.created"
4. EventBus notifica subscribers:
   a. Logger: registra em events_log
   b. Metrics: incrementa contador
```

### 5.2. Fluxo de Processamento de Webhook

```
1. Stark Bank envia POST /webhooks/invoice
2. WebhookReceiver:
   a. Valida assinatura digital
   b. Parseia payload JSON
3. WebhookProcessor:
   a. Extrai dados (invoice_id, amount, fee)
   b. Calcula net_amount = amount - fee
   c. Atualiza invoice via InvoiceRepository
   d. Publica evento "invoice.paid"
4. TransferHandler (subscriber de "invoice.paid"):
   a. Escuta evento
   b. Aciona TransferService
5. TransferService:
   a. Verifica se transferência já existe (idempotência)
   b. Cria transfer via StarkTransferAPI (com retry)
   c. Salva no banco via TransferRepository
   d. Publica evento "transfer.completed"
6. WebhookReceiver retorna HTTP 200
```

### 5.3. Fluxo de Transferência

```
1. TransferHandler recebe evento "invoice.paid"
2. TransferHandler:
   a. Extrai invoice_id do evento
   b. Carrega invoice do banco
   c. Calcula net_amount
3. TransferService:
   a. Verifica transferência existente via external_id
   b. Se existe: retorna existente (idempotência)
   c. Se não existe:
      i. Monta payload de transferência
      ii. Cria via StarkTransferAPI (com retry)
      iii. Salva no banco com status="created"
      iv. Publica evento "transfer.initiated"
```

### 5.4. Fluxo de Processamento de Webhook de Transfer

```
1. Stark Bank envia POST /webhooks/transfer
2. WebhookReceiver:
   a. Valida assinatura digital
   b. Parseia payload JSON
3. TransferWebhookProcessor:
   a. Extrai dados (transfer_id, status)
   b. Busca transferência no banco via stark_transfer_id
   c. Atualiza status da transferência
   d. Salva updated_at timestamp
   e. Decide qual evento publicar:
      - status="processing" → publica "transfer.processing"
      - status="success" → publica "transfer.completed" + atualiza completed_at
      - status="failed" → publica "transfer.failed" + salva error_message
4. EventBus notifica subscribers:
   a. Logger: registra em events_log
   b. Metrics: atualiza contadores
   c. Alertas: notifica se falha
5. WebhookReceiver retorna HTTP 200
```

**Estados de Transfer pelo Stark Bank:**
- `created` - Transferência criada (status local inicial)
- `processing` - Em processamento no Stark Bank
- `success` - Transferência concluída com sucesso
- `failed` - Transferência falhou (erro bancário, saldo insuficiente, etc)

### 5.5. Fluxo de Retry

```
1. Operação falha com erro retriável
2. RetryLogic:
   a. Verifica tipo de erro
   b. Se erro retriável e tentativas < 5:
      i. Incrementa retry_count
      ii. Registra last_retry_at
      iii. Aguarda delay (backoff exponencial)
      iv. Executa novamente
   c. Se erro não-retriável ou tentativas = 5:
      i. Salva error_message
      ii. Atualiza status para "failed"
      iii. Publica evento "operation.failed"
      iv. Lança exceção
```

## 6. Estratégias de Resiliência

### 6.1. Retry com Backoff Exponencial

**Configuração:**
- Max attempts: 5
- Delays: [0s, 60s, 120s, 240s, 480s]
- Total max time: ~15 minutos

**Erros Retriáveis:**
- `TimeoutError`: Timeout de conexão/leitura
- `RateLimitError`: HTTP 429 (Too Many Requests)
- `ServerError`: HTTP 5xx (500, 502, 503, 504)
- `ConnectionError`: Falha de rede

**Erros Não-Retriáveis:**
- `ValidationError`: HTTP 422 (Unprocessable Entity)
- `AuthenticationError`: HTTP 401 (Unauthorized)
- `PermissionError`: HTTP 403 (Forbidden)
- `NotFoundError`: HTTP 404 (Not Found)
- `BadRequestError`: HTTP 400 (Bad Request)

### 6.2. Idempotência

**Transferências:**
- Usar `external_id = invoice-{invoice_id}`
- Stark Bank garante: mesma external_id = mesma transfer
- Antes de criar: verificar se já existe no banco local

**Webhooks:**
- Podem ser enviados múltiplas vezes
- Processar sempre, mas não duplicar transferência
- Status da invoice garante idempotência

### 6.3. Persistência de Estado

**Registros de Retry:**
```python
invoice.retry_count = 0
invoice.last_retry_at = None
invoice.error_message = None

# A cada retry
invoice.retry_count += 1
invoice.last_retry_at = datetime.now()

# Se falhar definitivamente
invoice.status = "failed"
invoice.error_message = str(error)
```

**Auditoria Completa:**
- Todos eventos salvos em `events_log`
- Permite replay manual se necessário
- Facilita debugging

### 6.4. Circuit Breaker (Futuro)

**Não implementado na v1.0, mas preparado para:**
- Detectar falhas consecutivas
- "Abrir circuito" temporariamente
- Recuperar automaticamente quando serviço volta

## 7. Segurança

### 7.1. Autenticação

**API Key (para endpoints de consulta):**
```
Header: X-API-Key: <secret-key>
```
- Comparação segura (constant-time)
- Gerada e armazenada em variável de ambiente

**Digital Signature (para webhooks):**
```
Header: Digital-Signature: <ecdsa-signature>
```
- Validação usando public key do Stark Bank
- Previne webhooks forjados

### 7.2. Autorização

**Modelo simples:**
- API Key: acesso completo a leitura
- Webhooks: sem autenticação, mas validação de assinatura
- Health check: público

**Futuro:**
- Implementar roles (admin, readonly)
- Rate limiting por API Key
- OAuth2 para integrações externas

### 7.3. Proteção de Dados

**Logs:**
- Não logar API Keys ou senhas
- Mascarar CPF/CNPJ parcialmente
- Nunca logar payloads de webhooks completos (dados sensíveis)

**Banco de Dados:**
- SQLite file com permissões restritas (0600)
- Backup criptografado (futuro)

**Variáveis de Ambiente:**
```
STARK_BANK_PRIVATE_KEY=<base64-encoded-key>
STARK_BANK_PROJECT_ID=<project-id>
API_KEY=<random-secret-key>
DATABASE_URL=sqlite:///./stark_bank.db
```

### 7.4. HTTPS

**Produção (Railway):**
- HTTPS obrigatório
- Certificado gerenciado automaticamente
- Redirect de HTTP para HTTPS

**Desenvolvimento:**
- HTTP permitido (localhost)

## 8. Observabilidade

### 8.1. Logging

**Estrutura:**
- Formato: JSON
- Níveis: DEBUG, INFO, WARNING, ERROR
- Context: correlation_id, module, event

**Destinos:**
- Console (stdout) - para Railway
- Arquivo: `logs/app.log` - rotação diária

**Exemplo:**
```json
{
    "timestamp": "2026-02-14T10:30:00.123Z",
    "level": "INFO",
    "correlation_id": "req-abc123",
    "module": "invoices.service",
    "event": "invoice_created",
    "message": "Invoice created successfully",
    "data": {
        "invoice_id": "uuid-123",
        "stark_invoice_id": "5678",
        "amount": 500.00,
        "retry_count": 0
    }
}
```

### 8.2. Metrics (Futuro)

**Contadores:**
- `invoices_created_total` - Total de invoices criadas
- `invoices_failed_total` - Total de falhas
- `webhooks_invoice_received_total` - Total de webhooks de invoice recebidos
- `webhooks_transfer_received_total` - Total de webhooks de transfer recebidos
- `transfers_initiated_total` - Total de transferências iniciadas
- `transfers_completed_total` - Total de transferências concluídas
- `transfers_failed_total` - Total de transferências falhadas

**Histogramas:**
- `invoice_creation_duration_seconds` - Tempo de criação
- `webhook_invoice_processing_duration_seconds` - Tempo de processamento de webhook de invoice
- `webhook_transfer_processing_duration_seconds` - Tempo de processamento de webhook de transfer
- `transfer_creation_duration_seconds` - Tempo de transferência

**Gauges:**
- `active_invoices` - Invoices com status=created
- `processing_transfers` - Transfers com status=processing

### 8.3. Tracing (Futuro)

**OpenTelemetry:**
- Trace completo de cada operação
- Correlation entre invoice → payment → transfer
- Visualização em Jaeger/Zipkin

### 8.4. Health Check

**Endpoint: GET /health**

```json
{
    "status": "healthy",
    "timestamp": "2026-02-14T10:30:00.123Z",
    "checks": {
        "database": "ok",
        "stark_api": "ok"
    },
    "version": "1.0.0",
    "uptime_seconds": 3600
}
```

## 9. Testing Strategy

### 9.1. Pirâmide de Testes

```
        ▲
       ╱ ╲
      ╱ E2E╲         (~10% - 5 testes)
     ╱─────╲
    ╱  Int  ╲        (~30% - 15 testes)
   ╱─────────╲
  ╱   Unit    ╲      (~60% - 30 testes)
 ╱─────────────╲
```

**Target:** 85%+ cobertura

### 9.2. Unit Tests

**Escopo:** Funções e métodos isolados

**Ferramentas:**
- pytest
- pytest-mock
- pytest-cov (cobertura)

**Exemplos:**
- Validação de CPF/CNPJ
- Cálculo de net_amount
- Parsing de webhooks
- Formatação de payloads
- Lógica de retry

**Mocking:**
- Stark Bank API (mock responses)
- Database (in-memory ou mock)
- Faker (seed fixo para previsibilidade)

### 9.3. Integration Tests

**Escopo:** Integração entre componentes

**Exemplos:**
- InvoiceService + InvoiceRepository + EventBus
- WebhookProcessor + InvoiceRepository
- TransferService + StarkAPI (mocked)
- Event flow: invoice.created → handlers

**Database:**
- SQLite in-memory (`:memory:`)
- Schema criado em setup

### 9.4. E2E Tests

**Escopo:** Fluxo completo

**Ferramentas:**
- TestClient do FastAPI
- pytest-asyncio

**Exemplos:**
1. **Invoice Creation Flow:**
   - Scheduler inicia
   - Invoices criadas
   - Salvos no banco
   - Eventos publicados

2. **Invoice Webhook Flow:**
   - POST /webhooks/invoice
   - Assinatura validada
   - Invoice atualizada
   - Transfer criada

3. **Transfer Webhook Flow:**
   - POST /webhooks/transfer
   - Assinatura validada
   - Transfer atualizada
   - Status processado corretamente

4. **Query Flow:**
   - GET /invoices com filtros
   - GET /invoices/{id}
   - GET /transfers com filtros
   - GET /transfers/{id}
   - Autenticação via API Key

**Stark Bank API:**
- Mock para E2E (não bater sandbox)

### 9.5. Fixtures

```python
# conftest.py

@pytest.fixture
def db_connection():
    """In-memory SQLite database"""
    conn = sqlite3.connect(":memory:")
    # Run migrations
    conn.execute(CREATE_INVOICES_TABLE)
    conn.execute(CREATE_TRANSFERS_TABLE)
    conn.execute(CREATE_EVENTS_LOG_TABLE)
    yield conn
    conn.close()

@pytest.fixture
def mock_stark_api():
    """Mock Stark Bank API"""
    api = Mock(spec=StarkInvoiceAPI)
    api.create_invoice.return_value = InvoiceResponse(
        id="stark-123",
        status="created",
        ...
    )
    return api

@pytest.fixture
def event_bus():
    """Real EventBus instance"""
    return EventBus()
```

### 9.6. Test Coverage

**Por Módulo:**
- `invoices/` - 90%+ (lógica crítica)
- `webhooks/` - 90%+ (segurança crítica)
- `transfers/` - 90%+ (dinheiro envolvido)
- `shared/` - 80%+
- `main.py` - 70%+ (integração)

**Executar:**
```bash
pytest --cov=src --cov-report=html --cov-report=term
```

## 10. Configuration Management

### 10.1. Variáveis de Ambiente

```bash
# .env (desenvolvimento)

# Stark Bank
STARK_BANK_ENVIRONMENT=sandbox
STARK_BANK_PROJECT_ID=5656565656565656
STARK_BANK_PRIVATE_KEY=<base64-encoded-pem>

# API
API_KEY=dev-secret-key-12345
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_URL=sqlite:///./stark_bank.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Scheduler
SCHEDULER_ENABLED=true
SCHEDULER_INTERVAL_HOURS=3
SCHEDULER_DURATION_HOURS=24
```

### 10.2. Settings Module

```python
# src/config/settings.py

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Settings:
    # Stark Bank
    stark_environment: str
    stark_project_id: str
    stark_private_key: str
    
    # API
    api_key: str
    api_host: str
    api_port: int
    
    # Database
    database_url: str
    
    # Logging
    log_level: str
    log_file: str
    
    # Scheduler
    scheduler_enabled: bool
    scheduler_interval_hours: int
    scheduler_duration_hours: int
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables"""
        return cls(
            stark_environment=os.getenv("STARK_BANK_ENVIRONMENT", "sandbox"),
            stark_project_id=os.getenv("STARK_BANK_PROJECT_ID"),
            stark_private_key=os.getenv("STARK_BANK_PRIVATE_KEY"),
            api_key=os.getenv("API_KEY"),
            api_host=os.getenv("API_HOST", "0.0.0.0"),
            api_port=int(os.getenv("API_PORT", "8000")),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./stark_bank.db"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", "logs/app.log"),
            scheduler_enabled=os.getenv("SCHEDULER_ENABLED", "true").lower() == "true",
            scheduler_interval_hours=int(os.getenv("SCHEDULER_INTERVAL_HOURS", "3")),
            scheduler_duration_hours=int(os.getenv("SCHEDULER_DURATION_HOURS", "24")),
        )

# Singleton
settings = Settings.from_env()
```

### 10.3. Constants

```python
# src/config/constants.py

# Stark Bank Transfer Destination
STARK_BANK_ACCOUNT = {
    "bank_code": "20018183",
    "branch_code": "0001",
    "account_number": "6341320293482496",
    "account_type": "payment",
    "tax_id": "20.018.183/0001-80",
    "name": "Stark Bank S.A."
}

# Invoice Configuration
INVOICE_MIN_AMOUNT = 10000  # R$ 100,00 (centavos)
INVOICE_MAX_AMOUNT = 100000  # R$ 1.000,00 (centavos)
INVOICE_DUE_DAYS = 3
INVOICE_MIN_BATCH_SIZE = 8
INVOICE_MAX_BATCH_SIZE = 12

# CPF/CNPJ
CPF_WEIGHT = 0.7  # 70% CPF, 30% CNPJ

# Retry Configuration
RETRY_MAX_ATTEMPTS = 5
RETRY_DELAYS = [0, 60, 120, 240, 480]  # segundos

# Status
INVOICE_STATUS_CREATED = "created"
INVOICE_STATUS_PAID = "paid"
INVOICE_STATUS_FAILED = "failed"
INVOICE_STATUS_CANCELED = "canceled"
INVOICE_STATUS_EXPIRED = "expired"

TRANSFER_STATUS_CREATED = "created"
TRANSFER_STATUS_PROCESSING = "processing"
TRANSFER_STATUS_SUCCESS = "success"
TRANSFER_STATUS_FAILED = "failed"

# Events
EVENT_INVOICE_CREATED = "invoice.created"
EVENT_INVOICE_PAID = "invoice.paid"
EVENT_TRANSFER_INITIATED = "transfer.initiated"
EVENT_TRANSFER_PROCESSING = "transfer.processing"
EVENT_TRANSFER_COMPLETED = "transfer.completed"
EVENT_TRANSFER_FAILED = "transfer.failed"
EVENT_OPERATION_FAILED = "operation.failed"
```

## 11. Deployment

### 11.1. Railway

**Plataforma:** Railway (free tier)

**Vantagens:**
- Deploy automático via Git
- HTTPS nativo
- Logs centralizados
- Variáveis de ambiente
- Domínio gratuito

**Configuração:**

```toml
# Procfile (Railway)
web: uvicorn src.main:app --host 0.0.0.0 --port $PORT
scheduler: python src/scheduler.py
```

**Nota:** Railway free tier permite 1 processo. Solução:
- Opção 1: Rodar scheduler em thread dentro da API
- Opção 2: Usar Railway Pro (2 processos)
- **Escolhido: Opção 1** (thread dentro da API)

### 11.2. Environment Variables (Railway)

```
STARK_BANK_ENVIRONMENT=sandbox
STARK_BANK_PROJECT_ID=<from-stark-bank>
STARK_BANK_PRIVATE_KEY=<base64-encoded>
API_KEY=<generate-random-secure>
DATABASE_URL=sqlite:///./data/stark_bank.db
LOG_LEVEL=INFO
SCHEDULER_ENABLED=true
```

### 11.3. Database Persistence

**Problema:** Railway free tier não persiste arquivos

**Solução:**
- Usar volume montado (Railway suporta)
- Configurar volume: `/app/data`
- Database path: `/app/data/stark_bank.db`

**Alternativa (se volume não disponível):**
- PostgreSQL gratuito da Railway
- Migrar de SQLite para PostgreSQL

### 11.4. Build & Startup

```yaml
# railway.toml (exemplo)
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn src.main:app --host 0.0.0.0 --port $PORT"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

**Build steps:**
1. Detectar Python 3.14
2. Instalar dependências (pyproject.toml)
3. Run migrations (startup script)
4. Start API + Scheduler

### 11.5. Monitoring

**Railway Dashboard:**
- CPU/Memory usage
- Request logs
- Error logs
- Uptime

**Custom Health Check:**
```bash
# Railway health check endpoint
curl https://stark-bank-challenge.railway.app/health
```

## 12. Development Workflow

### 12.1. Local Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd stark-bank-challenge

# 2. Install dependencies (exemplo com rye)
rye sync

# 3. Setup environment
cp .env.example .env
# Edit .env with your Stark Bank credentials

# 4. Run migrations
python -m src.database.migrations

# 5. Run application
# Terminal 1 - API
uvicorn src.main:app --reload

# Terminal 2 - Scheduler (or use thread mode)
python src/scheduler.py
```

### 12.2. Linting & Formatting

```bash
# Ruff (linting + formatting)
ruff check src/
ruff format src/

# Type checking
mypy src/
```

### 12.3. Testing

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific module
pytest tests/unit/invoices/

# Watch mode
pytest-watch
```

### 12.4. Git Workflow

**Branches:**
- `main` - Produção (Railway auto-deploy)
- `develop` - Desenvolvimento
- `feature/<name>` - Features
- `fix/<name>` - Bugfixes

**Commits:**
- feat: Nova funcionalidade
- fix: Correção de bug
- refactor: Refatoração
- docs: Documentação
- test: Testes
- chore: Manutenção

**Exemplo:**
```
feat(invoices): add invoice generation with retry logic

- Implement InvoiceGenerator class
- Add retry decorator with exponential backoff
- Add unit tests for retry behavior
```

## 13. Troubleshooting

### 13.1. Problemas Comuns

#### Erro: "Invalid Private Key"
**Causa:** Private key do Stark Bank incorreta ou mal formatada

**Solução:**
```bash
# Verificar formato (deve ser base64)
echo $STARK_BANK_PRIVATE_KEY | base64 -d

# Gerar nova key no dashboard Stark Bank
```

#### Erro: "Database is Locked"
**Causa:** Concorrência no SQLite

**Solução:**
```python
# Habilitar WAL mode
conn.execute("PRAGMA journal_mode=WAL")

# Timeout maior
conn = sqlite3.connect("db.sqlite", timeout=30)
```

#### Erro: "Webhook Signature Invalid"
**Causa:** Public key incorreta ou payload modificado

**Solução:**
```python
# Verificar public key
logger.debug(f"Public key: {public_key[:20]}...")

# Logar payload raw
logger.debug(f"Raw payload: {request.body}")
```

#### Scheduler Não Executa
**Causa:** Thread não iniciada ou exceção silenciosa

**Solução:**
```python
# Adicionar logs
logger.info("Scheduler started")
logger.info(f"Next run: {scheduler.get_jobs()}")

# Verificar exceções
try:
    scheduler.start()
except Exception as e:
    logger.error(f"Scheduler failed: {e}")
```

### 13.2. Debugging

**FastAPI Debug Mode:**
```bash
uvicorn src.main:app --reload --log-level debug
```

**Logs Detalhados:**
```python
# Temporary debug logging
logger.setLevel(logging.DEBUG)
```

**Database Inspection:**
```bash
sqlite3 stark_bank.db

.tables
.schema invoices
SELECT * FROM invoices LIMIT 5;
SELECT * FROM events_log ORDER BY timestamp DESC LIMIT 10;
```

## 14. Future Improvements

### 14.1. Short Term (v1.1)

- [ ] PostgreSQL como opção de banco
- [ ] Circuit breaker pattern
- [ ] Rate limiting em endpoints
- [ ] Metrics com Prometheus
- [ ] Dashboard de monitoramento
- [ ] Retry manual de operações falhadas

## 15. Conclusão

### 15.1. Destaques da Arquitetura

1. **Modular:** Fácil de entender, testar e evoluir
2. **Resiliente:** Retry automático e tratamento de falhas
3. **Rastreável:** Logging estruturado e auditoria completa
4. **Seguro:** Validação de assinaturas e API Keys
5. **Testável:** Cobertura > 85% com testes claros
6. **Documentado:** Arquitetura e API completamente documentadas

### 15.2. Alinhamento com Requisitos

✅ Monolito modular  
✅ Event-driven architecture  
✅ Retry com backoff exponencial  
✅ Validação de CPF/CNPJ  
✅ Idempotência de transferências  
✅ Logging estruturado  
✅ Segurança (API Key + Assinatura)  
✅ Python 3.14 sem Pydantic  
✅ FastAPI + SQLite  
✅ Testes > 85% cobertura  

### 15.3. Trade-offs

**Escolhas:**
- SQLite (simplicidade) vs PostgreSQL (performance)
- In-memory Event Bus (simplicidade) vs RabbitMQ (escalabilidade)
- Monolito (deploy simples) vs Microserviços (escalabilidade)
- Thread scheduler (single process) vs Process (Railway free tier)

**Justificativa:**
- MVP focado em demonstrar capacidades técnicas
- Trade-offs documentados para evolução futura
- Arquitetura permite migração gradual

### 15.4. Aprendizados

- Integração com APIs bancárias requer resiliência extrema
- Event-driven facilita auditoria e debugging
- Idempotência é crítica para operações financeiras
- Testes são investimento, não custo
- Documentação é parte do produto

---

**Status:** Documento vivo, atualizado conforme implementação
