# Plano de Implementação Gradual
# Stark Bank Challenge

**Versão:** 1.0  
**Data:** Fevereiro 2026  
**Baseado em:** [architecture.md](architecture.md)

## Visão Geral

Este documento descreve o plano de implementação gradual do sistema, organizado em fases incrementais que permitem:
- ✅ Validação contínua através de testes
- ✅ Deploy progressivo de funcionalidades
- ✅ Feedback rápido em cada etapa
- ✅ Minimização de riscos

## Estratégia de Implementação

### Princípios

1. **Bottom-Up:** Começar pelos componentes base (shared) e construir módulos de domínio sobre eles
2. **Incremental:** Cada fase entrega funcionalidade testável e potencialmente deployável
3. **Test-First:** Testes acompanham a implementação em cada fase
4. **Integration Early:** Integrar componentes o mais cedo possível para detectar problemas

### Critérios de Conclusão por Fase

Cada fase só é considerada completa quando:
- ✅ Código implementado conforme arquitetura
- ✅ Testes unitários com cobertura > 80%
- ✅ Testes de integração passando
- ✅ Documentação atualizada
- ✅ Code review realizado
- ✅ Deploy em ambiente de dev bem-sucedido

---

## FASE 0: Setup e Fundação

**Duração Estimada:** 1 dia  
**Objetivo:** Preparar ambiente de desenvolvimento e estrutura base do projeto

### Tarefas

#### 0.1. Estrutura de Projeto
- [X] Criar estrutura completa de diretórios conforme [architecture.md](architecture.md#31-estrutura-de-diretórios)
- [X] Inicializar gerenciador de dependências (Rye/Poetry)
- [X] Configurar `.gitignore`
- [X] Criar arquivos `__init__.py` em todos os módulos

#### 0.2. Dependências
- [X] Criar `pyproject.toml` com todas as dependências
  ```toml
  [project]
  name = "stark-bank-challenge"
  version = "1.0.0"
  requires-python = ">=3.14"
  dependencies = [
      "fastapi>=0.115.0",
      "uvicorn[standard]>=0.30.0",
      "httpx>=0.28.0",
      "starkbank>=2.14.0",
      "apscheduler>=3.10.0",
      "validate-docbr>=1.10.0",
      "faker>=33.0.0",
      "python-dotenv>=1.0.0"
  ]
  
  [project.optional-dependencies]
  dev = [
      "pytest>=8.3.0",
      "pytest-asyncio>=0.24.0",
      "pytest-cov>=5.0.0",
      "pytest-mock>=3.14.0",
      "ruff>=0.8.0",
      "mypy>=1.11.0"
  ]
  ```
- [X] Instalar dependências: `rye sync` ou `poetry install`

#### 0.3. Configuração
- [X] Criar `.env.example` com todas as variáveis necessárias
- [X] Criar `src/config/settings.py` - Settings dataclass
- [X] Criar `src/config/constants.py` - Constantes de negócio
- [X] Documentar variáveis de ambiente no README

#### 0.4. Testing Setup
- [X] Configurar `pytest.ini` ou `pyproject.toml` com configurações pytest
- [X] Criar `tests/conftest.py` com fixtures base
- [X] Configurar cobertura de testes (pytest-cov)
- [x] Criar estrutura de diretórios de testes

#### 0.5. Linting & Formatting
- [X] Configurar Ruff no `pyproject.toml`
- [X] Criar script de lint: `ruff check src/`
- [X] Criar script de format: `ruff format src/`
- [X] Configurar pre-commit hooks (opcional)

#### 0.6. Documentação Base
- [X] Criar README.md com instruções de setup
- [X] Documentar estrutura de projeto
- [X] Criar CONTRIBUTING.md com workflow de desenvolvimento

### Entregáveis Fase 0
- ✅ Projeto estruturado e configurado
- ✅ Dependências instaladas
- ✅ Ambiente de testes configurado
- ✅ Documentação básica criada

### Validação
```bash
# Verificar estrutura
tree src/

# Verificar dependências
rye list  # ou poetry show

# Verificar testes
pytest --collect-only

# Verificar linting
ruff check src/
```

---

## FASE 1: Shared Components - Foundation

**Duração Estimada:** 2-3 dias  
**Objetivo:** Implementar componentes compartilhados que serão usados por todos os módulos

### 1.1. Logger

**Arquivos:**
- `src/shared/utils/logger.py`

**Implementação:**
- [X] Classe `StructuredLogger` com formato JSON
- [X] Suporte a níveis: DEBUG, INFO, WARNING, ERROR
- [X] Context injection (correlation_id, module, event)
- [X] Output para console e arquivo com rotação
- [X] Função helper `get_logger(module_name)`

**Testes:**
- [X] `tests/unit/shared/utils/test_logger.py`
- [X] Validar formato JSON
- [X] Validar níveis de log
- [X] Validar context injection
- [X] Validar rotação de arquivos

**Exemplo de uso:**
```python
logger = get_logger("invoices.service")
logger.info("Invoice created", data={"invoice_id": "123", "amount": 500.00})
```

### 1.2. Custom Exceptions

**Arquivos:**
- `src/shared/utils/errors.py`

**Implementação:**
- [X] `StarkBankError` - Base exception
- [X] `RetriableError` - Erros que permitem retry
- [X] `NonRetriableError` - Erros que não permitem retry
- [X] `ValidationError` - Erros de validação
- [X] `AuthenticationError` - Erros de autenticação
- [X] `NotFoundError` - Recurso não encontrado
- [X] `TimeoutError` - Timeout de operação
- [X] `RateLimitError` - Rate limit excedido

**Testes:**
- [X] `tests/unit/shared/utils/test_errors.py`
- [X] Validar hierarquia de exceções
- [X] Validar mensagens de erro

### 1.3. Validators

**Arquivos:**
- `src/shared/utils/validators.py`

**Implementação:**
- [X] `validate_cpf(cpf: str) -> bool` - usando validate-docbr
- [X] `validate_cnpj(cnpj: str) -> bool` - usando validate-docbr
- [X] `validate_tax_id(tax_id: str) -> bool` - detecta e valida CPF ou CNPJ
- [X] `format_cpf(cpf: str) -> str` - formata com pontos e traços
- [X] `format_cnpj(cnpj: str) -> str` - formata com pontos e traços
- [X] `clean_tax_id(tax_id: str) -> str` - remove formatação

**Testes:**
- [X] `tests/unit/shared/utils/test_validators.py`
- [X] Testes com CPFs válidos e inválidos
- [X] Testes com CNPJs válidos e inválidos
- [X] Testes de formatação
- [X] Edge cases (None, vazio, caracteres especiais)

### 1.4. Data Generator

**Arquivos:**
- `src/shared/utils/data_generator.py`

**Implementação:**
- [X] Classe `DataGenerator` wrapper do Faker
- [X] `generate_valid_cpf() -> str` - CPF válido
- [X] `generate_valid_cnpj() -> str` - CNPJ válido
- [X] `generate_person_data() -> dict` - nome, CPF, email
- [X] `generate_company_data() -> dict` - nome, CNPJ, email
- [X] `generate_customer_data(prefer_cpf: bool = True) -> dict` - 70% CPF, 30% CNPJ
- [X] Configuração de locale pt_BR

**Testes:**
- [X] `tests/unit/shared/utils/test_data_generator.py`
- [X] Validar CPFs gerados
- [X] Validar CNPJs gerados
- [X] Validar distribuição CPF/CNPJ (estatística)
- [X] Validar formato de emails

### 1.5. Database Layer

**Arquivos:**
- `src/shared/database/connection.py`
- `src/shared/database/migrations.py`
- `src/shared/database/base_repository.py`
- `migrations/001_initial_schema.sql`

**Implementação:**

**connection.py:**
- [X] `DatabaseConnection` - Singleton pattern
- [X] Connection pool com SQLite
- [X] WAL mode habilitado
- [X] Timeout configurável
- [X] Context manager para transações
- [X] Função `get_db() -> sqlite3.Connection`

**migrations.py:**
- [X] `MigrationRunner` - executa migrations
- [X] Tabela `schema_migrations` para controle
- [X] `run_migrations()` - aplica migrations pendentes
- [X] `rollback_migration()` - rollback de migration

**001_initial_schema.sql:**
- [X] Tabela `invoices` - conforme arquitetura
- [X] Tabela `transfers` - conforme arquitetura
- [X] Tabela `events_log` - conforme arquitetura
- [X] Índices necessários
- [X] Constraints (FK, UNIQUE)

**base_repository.py:**
- [X] `BaseRepository` - classe abstrata
- [X] Métodos base: `_execute()`, `_fetch_one()`, `_fetch_all()`
- [X] Context manager para transações
- [X] Logging de queries
- [X] Exception handling

**Testes:**
- [X] `tests/unit/shared/database/test_connection.py`
- [X] `tests/unit/shared/database/test_migrations.py`
- [X] Validar singleton pattern
- [X] Validar WAL mode
- [X] Validar transações
- [X] Validar migrations (apply/rollback)
- [X] Usar in-memory database (`:memory:`)

### 1.6. Event Bus

**Arquivos:**
- `src/shared/events/bus.py`
- `src/shared/events/types.py`
- `src/shared/events/logger.py`

**Implementação:**

**types.py:**
- [X] Dataclass `Event` - event_id, event_type, payload, metadata, timestamp
- [X] Enum `EventType` - todos tipos de eventos do sistema
- [X] Type hints para handlers: `EventHandler = Callable[[Event], None]`

**bus.py:**
- [X] Classe `EventBus` - Singleton pattern
- [X] `subscribe(event_type: str, handler: EventHandler) -> None`
- [X] `unsubscribe(event_type: str, handler: EventHandler) -> None`
- [X] `publish(event_type: str, payload: dict, metadata: dict = None) -> None`
- [X] Registry de handlers: `Dict[str, List[EventHandler]]`
- [X] Logging de todos eventos publicados
- [X] Exception handling em handlers (não deve quebrar publicação)

**logger.py:**
- [X] `EventLogger` - persiste eventos no banco
- [X] Subscriber automático de todos eventos
- [X] Salva em `events_log` table
- [X] `get_events(event_type: str = None, limit: int = 100) -> List[Event]`

**Testes:**
- [X] `tests/unit/shared/events/test_bus.py`
- [X] `tests/unit/shared/events/test_logger.py`
- [X] Validar subscribe/unsubscribe
- [X] Validar publish (síncrono)
- [X] Validar múltiplos handlers para mesmo evento
- [X] Validar que falha em handler não quebra outros
- [X] Validar persistência em events_log
- [X] Mock de handlers

### Entregáveis Fase 1
- ✅ Logger estruturado funcionando
- ✅ Validadores de CPF/CNPJ
- ✅ Gerador de dados fake
- ✅ Database com migrations
- ✅ Event Bus operacional
- ✅ Testes unitários > 80% cobertura
- ✅ Documentação de APIs

### Validação Fase 1
```bash
# Testes
pytest tests/unit/shared/ -v --cov=src/shared

# Validar database
python -c "from src.shared.database.migrations import run_migrations; run_migrations()"
sqlite3 stark_bank.db ".tables"

# Validar event bus
python -c "from src.shared.events.bus import EventBus; bus = EventBus(); print('OK')"
```

---

## FASE 2: Stark Bank Integration Layer

**Duração Estimada:** 2-3 dias  
**Objetivo:** Implementar integração com API do Stark Bank com retry logic

### 2.1. Retry Logic

**Arquivos:**
- `src/shared/stark/retry.py`

**Implementação:**
- [X] Decorator `@retry_with_backoff` - configurável
- [X] Parâmetros: `max_attempts`, `delays`, `retriable_exceptions`, `non_retriable_exceptions`
- [X] Backoff exponencial: [0, 60, 120, 240, 480] segundos
- [X] Logging de cada tentativa
- [X] Persistência de retry_count
- [X] Raise após max_attempts

**Testes:**
- [X] `tests/unit/shared/stark/test_retry.py`
- [X] Mock de função que falha N vezes
- [X] Validar número de tentativas
- [X] Validar delays entre tentativas
- [X] Validar exceções retriáveis vs não-retriáveis
- [X] Validar logging

### 2.2. Stark Bank Client Base

**Arquivos:**
- `src/shared/stark/client.py`

**Implementação:**
- [X] Classe `StarkBankClient` - base class
- [X] Inicialização do SDK starkbank
- [X] Configuração de ambiente (sandbox/production)
- [X] Configuração de project_id e private_key
- [X] Logging de todas chamadas
- [X] Exception handling e mapeamento para custom exceptions
- [X] Rate limit handling

**Testes:**
- [X] `tests/unit/shared/stark/test_client.py`
- [X] Mock do SDK starkbank
- [X] Validar inicialização
- [X] Validar configuração de ambiente
- [X] Validar exception handling

### 2.3. Invoice API

**Arquivos:**
- `src/shared/stark/invoice_api.py`

**Implementação:**
- [X] Classe `StarkInvoiceAPI(StarkBankClient)`
- [X] `create_invoice(amount, tax_id, name, due_date, ...) -> InvoiceResponse` com retry
- [X] `get_invoice(invoice_id: str) -> InvoiceResponse`
- [X] `list_invoices(limit: int, after: str) -> List[InvoiceResponse]`
- [X] Dataclass `InvoiceResponse` para resposta padronizada
- [X] Validação de parâmetros
- [X] Conversão de amount para centavos (int)
- [X] Logging estruturado

**Testes:**
- [X] `tests/unit/shared/stark/test_invoice_api.py`
- [ ] `tests/integration/shared/stark/test_invoice_api_integration.py` (sandbox)
- [X] Mock de starkbank.invoice.create()
- [X] Validar retry em falhas
- [X] Validar conversão de valores
- [X] Validar validação de parâmetros
- [ ] **Teste real:** criar invoice no sandbox (integration test)

### 2.4. Transfer API

**Arquivos:**
- `src/shared/stark/transfer_api.py`

**Implementação:**
- [X] Classe `StarkTransferAPI(StarkBankClient)`
- [X] `create_transfer(amount, external_id, bank_code, ...) -> TransferResponse` com retry
- [X] `get_transfer(transfer_id: str) -> TransferResponse`
- [X] `list_transfers(limit: int, after: str) -> List[TransferResponse]`
- [X] Dataclass `TransferResponse` para resposta padronizada
- [X] Idempotência via `external_id`
- [X] Validação de parâmetros
- [X] Conversão de amount para centavos (int)
- [X] Logging estruturado

**Testes:**
- [X] `tests/unit/shared/stark/test_transfer_api.py`
- [ ] `tests/integration/shared/stark/test_transfer_api_integration.py` (sandbox)
- [X] Mock de starkbank.transfer.create()
- [X] Validar retry em falhas
- [X] Validar idempotência (mesmo external_id)
- [X] Validar conversão de valores
- [ ] **Teste real:** criar transfer no sandbox (integration test)

### Entregáveis Fase 2
- ✅ Retry logic robusto
- ✅ Cliente Stark Bank base
- ✅ Invoice API com retry
- ✅ Transfer API com retry
- ✅ Testes unitários > 80%
- ✅ Testes de integração com sandbox passando
- ✅ Documentação de APIs

### Validação Fase 2
```bash
# Testes unitários
pytest tests/unit/shared/stark/ -v

# Testes de integração (requer credenciais sandbox)
pytest tests/integration/shared/stark/ -v

# Teste manual
python -m examples.test_stark_invoice
python -m examples.test_stark_transfer
```

---

## FASE 3: Security Layer

**Duração Estimada:** 1-2 dias  
**Objetivo:** Implementar segurança (API Key e validação de assinatura de webhooks)

### 3.1. API Key Authentication

**Arquivos:**
- `src/shared/security/api_key.py`

**Implementação:**
- [X] Função `verify_api_key(api_key: str) -> bool` - constant-time comparison
- [X] FastAPI Dependency `get_api_key_dependency` - para uso em endpoints
- [X] Classe `APIKeyHeader` - extrai header X-API-Key
- [X] Exception `InvalidAPIKeyError`
- [X] Logging de tentativas de autenticação

**Testes:**
- [X] `tests/unit/shared/security/test_api_key.py`
- [X] Validar API key correta
- [X] Validar API key incorreta
- [X] Validar constant-time comparison
- [X] Validar logging de falhas

### 3.2. Webhook Signature Validation

**Arquivos:**
- `src/shared/security/signature.py`

**Implementação:**
- [X] Função `validate_webhook_signature(payload: bytes, signature: str, public_key: str) -> bool`
- [X] Usar ECDSA para validação (conforme documentação Stark Bank)
- [X] Carregar public key do Stark Bank
- [X] Exception `InvalidSignatureError`
- [X] Logging de validações (sucesso/falha)

**Testes:**
- [X] `tests/unit/shared/security/test_signature.py`
- [X] Mock de assinatura válida
- [X] Mock de assinatura inválida
- [X] Validar parsing de public key
- [X] Validar ECDSA verification

### 3.3. Security Constants

**Arquivos:**
- `src/shared/security/constants.py`

**Implementação:**
- [X] Public key do Stark Bank (sandbox e production)
- [X] Headers de segurança
- [X] Timeout de requests
- [X] Rate limits

### Entregáveis Fase 3
- ✅ API Key authentication funcionando
- ✅ Webhook signature validation
- ✅ Testes unitários > 90% (segurança é crítica)
- ✅ Documentação de segurança

### Validação Fase 3
```bash
# Testes
pytest tests/unit/shared/security/ -v --cov=src/shared/security

# Validar API Key
python -c "from src.shared.security.api_key import verify_api_key; print(verify_api_key('test-key'))"
```

---

## FASE 4: Invoices Module

**Duração Estimada:** 3-4 dias  
**Objetivo:** Implementar módulo completo de Invoices (geração, persistência, API)

### 4.1. Invoice Models

**Arquivos:**
- `src/modules/invoices/models.py`
- `src/modules/invoices/events.py`

**Implementação:**

**models.py:**
- [ ] Dataclass `InvoiceModel` - representa invoice no sistema
- [ ] Campos: id, stark_invoice_id, amount, customer_name, customer_tax_id, customer_email, status, created_at, paid_at, fee, net_amount, retry_count, last_retry_at, error_message
- [ ] Métodos: `to_dict()`, `from_dict()`, `calculate_net_amount()`
- [ ] Validação de campos

**events.py:**
- [ ] `InvoiceCreatedEvent` - payload da invoice criada
- [ ] `InvoiceCreationFailedEvent` - payload de falha
- [ ] Constantes de tipos de eventos

**Testes:**
- [ ] `tests/unit/modules/invoices/test_models.py`
- [ ] Validar criação de modelo
- [ ] Validar cálculo de net_amount
- [ ] Validar conversão to_dict/from_dict
- [ ] Validar validação de campos

### 4.2. Invoice Repository

**Arquivos:**
- `src/modules/invoices/repository.py`

**Implementação:**
- [ ] Classe `InvoiceRepository(BaseRepository)`
- [ ] `create(invoice: InvoiceModel) -> None`
- [ ] `get_by_id(invoice_id: str) -> Optional[InvoiceModel]`
- [ ] `get_by_stark_id(stark_id: str) -> Optional[InvoiceModel]`
- [ ] `update(invoice: InvoiceModel) -> None`
- [ ] `list(status: Optional[str], limit: int, offset: int) -> List[InvoiceModel]`
- [ ] `count(status: Optional[str]) -> int`
- [ ] Logging de operações
- [ ] Exception handling

**Testes:**
- [ ] `tests/unit/modules/invoices/test_repository.py`
- [ ] Mock de database
- [ ] Validar CRUD operations
- [ ] Validar queries com filtros
- [ ] Validar paginação

### 4.3. Invoice Generator

**Arquivos:**
- `src/modules/invoices/generator.py`

**Implementação:**
- [ ] Classe `InvoiceGenerator`
- [ ] `generate_batch(count: int) -> List[dict]` - gera dados de N invoices
- [ ] `_generate_single() -> dict` - gera dados de 1 invoice
- [ ] Usa `DataGenerator` para dados fake
- [ ] Valida CPF/CNPJ gerados
- [ ] Configuração: min/max amount, due days, CPF/CNPJ ratio
- [ ] Logging de invoices geradas

**Testes:**
- [ ] `tests/unit/modules/invoices/test_generator.py`
- [ ] Validar geração de batch (8-12 invoices)
- [ ] Validar valores dentro do range
- [ ] Validar CPF/CNPJ válidos
- [ ] Validar distribuição CPF/CNPJ (70/30)

### 4.4. Invoice Service

**Arquivos:**
- `src/modules/invoices/service.py`

**Implementação:**
- [ ] Classe `InvoiceService`
- [ ] `__init__(repository, stark_api, event_bus)`
- [ ] `create_invoice(invoice_data: dict) -> InvoiceModel` - cria invoice completa
  - [ ] Validar dados
  - [ ] Criar no Stark Bank (com retry)
  - [ ] Salvar no banco
  - [ ] Publicar evento `invoice.created`
  - [ ] Exception handling + publicar `invoice.creation_failed`
- [ ] `get_invoice(invoice_id: str) -> Optional[InvoiceModel]`
- [ ] `list_invoices(status, limit, offset) -> List[InvoiceModel]`
- [ ] `update_invoice_status(invoice_id, status, **kwargs) -> None`
- [ ] Logging estruturado

**Testes:**
- [ ] `tests/unit/modules/invoices/test_service.py`
- [ ] Mock de repository, stark_api, event_bus
- [ ] Validar fluxo completo de criação
- [ ] Validar retry em falhas
- [ ] Validar publicação de eventos
- [ ] Validar exception handling

### 4.5. Invoice API Endpoints

**Arquivos:**
- `src/modules/invoices/api.py`

**Implementação:**
- [ ] FastAPI Router `invoice_router`
- [ ] `POST /invoices` - criar invoice (protegido por API Key)
- [ ] `GET /invoices` - listar invoices (protegido por API Key)
  - Query params: status, limit, offset
- [ ] `GET /invoices/{invoice_id}` - buscar invoice (protegido por API Key)
- [ ] Response models (dict ou dataclass)
- [ ] Exception handling → HTTP status codes
- [ ] Logging de requests

**Testes:**
- [ ] `tests/integration/modules/invoices/test_api.py`
- [ ] Usar TestClient do FastAPI
- [ ] Mock de service
- [ ] Validar todos endpoints
- [ ] Validar autenticação (com/sem API Key)
- [ ] Validar responses e status codes

### Entregáveis Fase 4
- ✅ Módulo de Invoices completo
- ✅ Repository funcionando
- ✅ Generator criando invoices válidas
- ✅ Service com lógica de negócio
- ✅ API endpoints operacionais
- ✅ Testes unitários + integração > 85%
- ✅ Documentação de APIs

### Validação Fase 4
```bash
# Testes
pytest tests/unit/modules/invoices/ -v
pytest tests/integration/modules/invoices/ -v

# Teste manual de API
uvicorn src.main:app --reload
curl -X POST http://localhost:8000/invoices -H "X-API-Key: dev-key" -d '{...}'
curl -X GET http://localhost:8000/invoices -H "X-API-Key: dev-key"
```

---

## FASE 5: Webhooks Module

**Duração Estimada:** 3-4 dias  
**Objetivo:** Implementar recepção e processamento de webhooks (invoices e transfers)

### 5.1. Webhook Models

**Arquivos:**
- `src/modules/webhooks/models.py`
- `src/modules/webhooks/events.py`

**Implementação:**

**models.py:**
- [ ] Dataclass `WebhookEvent` - estrutura base de webhook
- [ ] Dataclass `InvoiceWebhookPayload` - parser de payload de invoice
- [ ] Dataclass `TransferWebhookPayload` - parser de payload de transfer
- [ ] Métodos de parsing e validação

**events.py:**
- [ ] `InvoicePaidEvent` - invoice paga confirmada
- [ ] `TransferProcessingEvent` - transfer em processamento
- [ ] `TransferCompletedEvent` - transfer concluída
- [ ] `TransferFailedEvent` - transfer falhou
- [ ] `WebhookValidationFailedEvent` - assinatura inválida

**Testes:**
- [ ] `tests/unit/modules/webhooks/test_models.py`
- [ ] Validar parsing de payloads reais (samples do Stark Bank)
- [ ] Validar campos obrigatórios
- [ ] Validar conversão de tipos

### 5.2. Webhook Validator

**Arquivos:**
- `src/modules/webhooks/validator.py`

**Implementação:**
- [ ] Classe `WebhookValidator`
- [ ] `validate_signature(payload: bytes, signature: str) -> bool`
- [ ] Wrapper sobre `security.signature.validate_webhook_signature`
- [ ] Logging de validações
- [ ] Exception handling

**Testes:**
- [ ] `tests/unit/modules/webhooks/test_validator.py`
- [ ] Mock de signature validation
- [ ] Validar assinatura válida
- [ ] Validar assinatura inválida
- [ ] Validar logging

### 5.3. Invoice Webhook Processor

**Arquivos:**
- `src/modules/webhooks/invoice_processor.py`

**Implementação:**
- [ ] Classe `InvoiceWebhookProcessor`
- [ ] `__init__(invoice_repository, event_bus)`
- [ ] `process(webhook_payload: InvoiceWebhookPayload) -> None`
  - [ ] Extrair dados (invoice_id, amount, fee, status)
  - [ ] Buscar invoice no banco via stark_invoice_id
  - [ ] Atualizar status da invoice
  - [ ] Calcular net_amount = amount - fee
  - [ ] Atualizar paid_at timestamp
  - [ ] Publicar evento `invoice.paid`
- [ ] Logging estruturado
- [ ] Exception handling

**Testes:**
- [ ] `tests/unit/modules/webhooks/test_invoice_processor.py`
- [ ] Mock de repository e event_bus
- [ ] Validar processamento de webhook de pagamento
- [ ] Validar cálculo de net_amount
- [ ] Validar atualização de invoice
- [ ] Validar publicação de evento

### 5.4. Transfer Webhook Processor

**Arquivos:**
- `src/modules/webhooks/transfer_processor.py`

**Implementação:**
- [ ] Classe `TransferWebhookProcessor`
- [ ] `__init__(transfer_repository, event_bus)`
- [ ] `process(webhook_payload: TransferWebhookPayload) -> None`
  - [ ] Extrair dados (transfer_id, status, error)
  - [ ] Buscar transfer no banco via stark_transfer_id
  - [ ] Atualizar status da transfer
  - [ ] Atualizar updated_at timestamp
  - [ ] Se status="success": atualizar completed_at, publicar `transfer.completed`
  - [ ] Se status="failed": salvar error_message, publicar `transfer.failed`
  - [ ] Se status="processing": publicar `transfer.processing`
- [ ] Logging estruturado
- [ ] Exception handling

**Testes:**
- [ ] `tests/unit/modules/webhooks/test_transfer_processor.py`
- [ ] Mock de repository e event_bus
- [ ] Validar processamento de status "processing"
- [ ] Validar processamento de status "success"
- [ ] Validar processamento de status "failed"
- [ ] Validar atualização de transfer
- [ ] Validar publicação de eventos

### 5.5. Webhook Receiver (API)

**Arquivos:**
- `src/modules/webhooks/receiver.py`
- `src/modules/webhooks/api.py`

**Implementação:**

**receiver.py:**
- [ ] Classe `WebhookReceiver`
- [ ] `__init__(validator, invoice_processor, transfer_processor, event_bus)`
- [ ] `receive_invoice_webhook(payload: bytes, signature: str) -> dict`
  - [ ] Validar assinatura
  - [ ] Parsear payload
  - [ ] Processar via InvoiceWebhookProcessor
  - [ ] Retornar {"status": "ok"}
- [ ] `receive_transfer_webhook(payload: bytes, signature: str) -> dict`
  - [ ] Validar assinatura
  - [ ] Parsear payload
  - [ ] Processar via TransferWebhookProcessor
  - [ ] Retornar {"status": "ok"}
- [ ] Exception handling robusto (sempre retornar 200 se possível)

**api.py:**
- [ ] FastAPI Router `webhook_router`
- [ ] `POST /webhooks/invoice` - recebe webhook de invoice (público, validado por assinatura)
- [ ] `POST /webhooks/transfer` - recebe webhook de transfer (público, validado por assinatura)
- [ ] Exception handling → sempre retornar 200 (exceto validation fatal)
- [ ] Logging de todos webhooks recebidos

**Testes:**
- [ ] `tests/unit/modules/webhooks/test_receiver.py`
- [ ] `tests/integration/modules/webhooks/test_api.py`
- [ ] Mock de processors
- [ ] Validar fluxo completo de webhook
- [ ] Validar validação de assinatura
- [ ] Validar exception handling
- [ ] Validar responses HTTP

### Entregáveis Fase 5
- ✅ Webhooks de invoice processados
- ✅ Webhooks de transfer processados
- ✅ Validação de assinatura funcionando
- ✅ API endpoints operacionais
- ✅ Testes unitários + integração > 85%
- ✅ Documentação de webhooks

### Validação Fase 5
```bash
# Testes
pytest tests/unit/modules/webhooks/ -v
pytest tests/integration/modules/webhooks/ -v

# Teste manual (simular webhook)
curl -X POST http://localhost:8000/webhooks/invoice \
  -H "Content-Type: application/json" \
  -H "Digital-Signature: <signature>" \
  -d '{"event": {"log": {...}}}'
```

---

## FASE 6: Transfers Module

**Duração Estimada:** 3-4 dias  
**Objetivo:** Implementar módulo de transferências (criação automática ao receber pagamento)

### 6.1. Transfer Models

**Arquivos:**
- `src/modules/transfers/models.py`
- `src/modules/transfers/events.py`

**Implementação:**

**models.py:**
- [ ] Dataclass `TransferModel` - representa transfer no sistema
- [ ] Campos: id, invoice_id, stark_transfer_id, external_id, amount, status, created_at, updated_at, completed_at, retry_count, last_retry_at, error_message
- [ ] Métodos: `to_dict()`, `from_dict()`
- [ ] Validação de campos

**events.py:**
- [ ] `TransferInitiatedEvent` - transfer iniciada
- [ ] `TransferProcessingEvent` - transfer em processamento
- [ ] `TransferCompletedEvent` - transfer concluída
- [ ] `TransferFailedEvent` - transfer falhou

**Testes:**
- [ ] `tests/unit/modules/transfers/test_models.py`
- [ ] Validar criação de modelo
- [ ] Validar conversão to_dict/from_dict
- [ ] Validar status transitions

### 6.2. Transfer Repository

**Arquivos:**
- `src/modules/transfers/repository.py`

**Implementação:**
- [ ] Classe `TransferRepository(BaseRepository)`
- [ ] `create(transfer: TransferModel) -> None`
- [ ] `get_by_id(transfer_id: str) -> Optional[TransferModel]`
- [ ] `get_by_stark_id(stark_id: str) -> Optional[TransferModel]`
- [ ] `get_by_external_id(external_id: str) -> Optional[TransferModel]` - para idempotência
- [ ] `get_by_invoice_id(invoice_id: str) -> Optional[TransferModel]`
- [ ] `update(transfer: TransferModel) -> None`
- [ ] `list(status: Optional[str], limit: int, offset: int) -> List[TransferModel]`
- [ ] `count(status: Optional[str]) -> int`
- [ ] Logging de operações

**Testes:**
- [ ] `tests/unit/modules/transfers/test_repository.py`
- [ ] Mock de database
- [ ] Validar CRUD operations
- [ ] Validar queries com filtros
- [ ] Validar busca por external_id (idempotência)

### 6.3. Transfer Service

**Arquivos:**
- `src/modules/transfers/service.py`

**Implementação:**
- [ ] Classe `TransferService`
- [ ] `__init__(repository, stark_api, event_bus, config)`
- [ ] `create_transfer(invoice: InvoiceModel) -> TransferModel` - cria transfer
  - [ ] Gerar external_id = f"invoice-{invoice.id}"
  - [ ] Verificar se transfer já existe (idempotência)
  - [ ] Calcular amount = invoice.net_amount
  - [ ] Montar payload com conta destino do Stark Bank (constants)
  - [ ] Criar via StarkTransferAPI (com retry)
  - [ ] Salvar no banco com status="created"
  - [ ] Publicar evento `transfer.initiated`
  - [ ] Exception handling + publicar `transfer.failed`
- [ ] `get_transfer(transfer_id: str) -> Optional[TransferModel]`
- [ ] `list_transfers(status, limit, offset) -> List[TransferModel]`
- [ ] `update_transfer_status(transfer_id, status, **kwargs) -> None`
- [ ] Logging estruturado

**Testes:**
- [ ] `tests/unit/modules/transfers/test_service.py`
- [ ] Mock de repository, stark_api, event_bus
- [ ] Validar fluxo completo de criação
- [ ] Validar idempotência (mesma invoice)
- [ ] Validar retry em falhas
- [ ] Validar publicação de eventos
- [ ] Validar conta destino (Stark Bank)

### 6.4. Transfer Handler (Event Subscriber)

**Arquivos:**
- `src/modules/transfers/handler.py`

**Implementação:**
- [ ] Classe `TransferHandler`
- [ ] `__init__(service, invoice_repository)`
- [ ] `handle_invoice_paid(event: Event) -> None` - subscriber de `invoice.paid`
  - [ ] Extrair invoice_id do evento
  - [ ] Carregar invoice do banco
  - [ ] Validar se invoice está paga
  - [ ] Chamar TransferService.create_transfer()
  - [ ] Logging estruturado
  - [ ] Exception handling (não deve quebrar event bus)
- [ ] Registrar handler no EventBus na inicialização

**Testes:**
- [ ] `tests/unit/modules/transfers/test_handler.py`
- [ ] Mock de service, repository, event_bus
- [ ] Validar processamento de evento `invoice.paid`
- [ ] Validar chamada a TransferService
- [ ] Validar exception handling

### 6.5. Transfer API Endpoints

**Arquivos:**
- `src/modules/transfers/api.py`

**Implementação:**
- [ ] FastAPI Router `transfer_router`
- [ ] `GET /transfers` - listar transfers (protegido por API Key)
  - Query params: status, limit, offset
- [ ] `GET /transfers/{transfer_id}` - buscar transfer (protegido por API Key)
- [ ] `GET /transfers/invoice/{invoice_id}` - buscar transfer por invoice (protegido por API Key)
- [ ] Response models
- [ ] Exception handling → HTTP status codes
- [ ] Logging de requests

**Testes:**
- [ ] `tests/integration/modules/transfers/test_api.py`
- [ ] Usar TestClient do FastAPI
- [ ] Mock de service
- [ ] Validar todos endpoints
- [ ] Validar autenticação
- [ ] Validar responses e status codes

### Entregáveis Fase 6
- ✅ Módulo de Transfers completo
- ✅ Criação automática ao receber pagamento
- ✅ Idempotência garantida
- ✅ Event handler funcionando
- ✅ API endpoints operacionais
- ✅ Testes unitários + integração > 85%
- ✅ Documentação de APIs

### Validação Fase 6
```bash
# Testes
pytest tests/unit/modules/transfers/ -v
pytest tests/integration/modules/transfers/ -v

# Teste E2E (simular fluxo completo)
# 1. Criar invoice
# 2. Simular webhook de pagamento
# 3. Verificar transfer criada automaticamente
```

---

## FASE 7: Scheduler & Main Application

**Duração Estimada:** 2-3 dias  
**Objetivo:** Implementar scheduler de geração de invoices e integrar todos módulos

### 7.1. Scheduler

**Arquivos:**
- `src/scheduler.py`

**Implementação:**
- [ ] Função `run_scheduler()` - entry point
- [ ] Configurar APScheduler com IntervalTrigger
- [ ] Job: `generate_invoices_job()`
  - [ ] Usar InvoiceGenerator para gerar batch
  - [ ] Usar InvoiceService para criar cada invoice
  - [ ] Logging de execução
  - [ ] Exception handling
- [ ] Configuração: intervalo (3h), duração (24h = 8 ciclos)
- [ ] Shutdown graceful
- [ ] Opção de rodar em thread ou processo separado

**Testes:**
- [ ] `tests/unit/test_scheduler.py`
- [ ] Mock de InvoiceService
- [ ] Validar agendamento
- [ ] Validar execução de job
- [ ] Validar shutdown

### 7.2. FastAPI Main Application

**Arquivos:**
- `src/main.py`

**Implementação:**
- [ ] FastAPI app instance
- [ ] Lifespan events:
  - [ ] `startup`:
    - [ ] Inicializar database (run migrations)
    - [ ] Inicializar EventBus
    - [ ] Registrar event handlers (TransferHandler)
    - [ ] Iniciar scheduler em thread (se configurado)
    - [ ] Logging de startup
  - [ ] `shutdown`:
    - [ ] Parar scheduler
    - [ ] Fechar database connections
    - [ ] Logging de shutdown
- [ ] Incluir routers:
  - [ ] `invoice_router` com prefix `/invoices`
  - [ ] `transfer_router` com prefix `/transfers`
  - [ ] `webhook_router` com prefix `/webhooks`
- [ ] Endpoint raiz: `GET /` - redirect para `/docs`
- [ ] Health check: `GET /health`
- [ ] Exception handlers globais
- [ ] CORS configuration (se necessário)
- [ ] Logging middleware

**Testes:**
- [ ] `tests/integration/test_main.py`
- [ ] Usar TestClient
- [ ] Validar startup/shutdown
- [ ] Validar health check
- [ ] Validar integração de routers

### 7.3. Health Check

**Arquivos:**
- `src/health.py`

**Implementação:**
- [ ] Função `check_health() -> dict`
- [ ] Verificar:
  - [ ] Database (executar query simples)
  - [ ] Stark Bank API (opcional - pode ser lento)
  - [ ] EventBus
- [ ] Retornar:
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-02-14T10:30:00.123Z",
    "checks": {
      "database": "ok",
      "event_bus": "ok"
    },
    "version": "1.0.0",
    "uptime_seconds": 3600
  }
  ```

**Testes:**
- [ ] `tests/unit/test_health.py`
- [ ] Validar health check com tudo OK
- [ ] Validar health check com database falha

### 7.4. Dependency Injection Setup

**Arquivos:**
- `src/dependencies.py`

**Implementação:**
- [ ] Factory functions para FastAPI Depends():
  - [ ] `get_db() -> sqlite3.Connection`
  - [ ] `get_event_bus() -> EventBus`
  - [ ] `get_invoice_repository() -> InvoiceRepository`
  - [ ] `get_invoice_service() -> InvoiceService`
  - [ ] `get_transfer_repository() -> TransferRepository`
  - [ ] `get_transfer_service() -> TransferService`
  - [ ] `get_webhook_validator() -> WebhookValidator`
- [ ] Singletons onde apropriado (EventBus, Database)

### Entregáveis Fase 7
- ✅ Scheduler gerando invoices a cada 3h
- ✅ FastAPI app completa e integrada
- ✅ Health check operacional
- ✅ Todos módulos integrados
- ✅ Testes de integração > 80%
- ✅ Sistema rodando end-to-end

### Validação Fase 7
```bash
# Rodar aplicação completa
uvicorn src.main:app --reload

# Verificar health
curl http://localhost:8000/health

# Verificar scheduler logs (deve criar invoices a cada 3h)
tail -f logs/app.log

# Verificar docs
open http://localhost:8000/docs
```

---

## FASE 8: End-to-End Tests

**Duração Estimada:** 2-3 dias  
**Objetivo:** Implementar testes E2E que validam fluxos completos

### 8.1. E2E Test Infrastructure

**Arquivos:**
- `tests/e2e/conftest.py`
- `tests/e2e/helpers.py`

**Implementação:**
- [ ] Fixtures para E2E:
  - [ ] `e2e_app` - FastAPI TestClient com database real/in-memory
  - [ ] `e2e_db` - Database isolada para cada teste
  - [ ] `mock_stark_api` - Mock de Stark Bank API para E2E
  - [ ] `sample_invoices` - Invoices de exemplo
- [ ] Helpers:
  - [ ] `create_test_invoice()` - cria invoice via API
  - [ ] `simulate_webhook()` - simula webhook com assinatura
  - [ ] `wait_for_event()` - aguarda evento ser publicado
  - [ ] `assert_transfer_created()` - valida transfer criada

### 8.2. E2E Test: Invoice Creation Flow

**Arquivos:**
- `tests/e2e/test_invoice_creation_flow.py`

**Testes:**
- [ ] `test_invoice_creation_success`
  - [ ] Scheduler aciona geração
  - [ ] Invoices criadas no Stark Bank (mock)
  - [ ] Invoices salvas no banco
  - [ ] Eventos `invoice.created` publicados
  - [ ] Validar todas invoices com status="created"

### 8.3. E2E Test: Payment to Transfer Flow

**Arquivos:**
- `tests/e2e/test_payment_to_transfer_flow.py`

**Testes:**
- [ ] `test_complete_payment_flow`
  - [ ] Criar invoice via API
  - [ ] Simular webhook de pagamento
  - [ ] Validar invoice com status="paid"
  - [ ] Validar transfer criada automaticamente
  - [ ] Validar transfer com external_id correto
  - [ ] Validar eventos publicados
  - [ ] Validar logs
- [ ] `test_idempotency_multiple_webhooks`
  - [ ] Criar invoice
  - [ ] Simular webhook de pagamento 3 vezes
  - [ ] Validar apenas 1 transfer criada
- [ ] `test_payment_flow_with_retry`
  - [ ] Criar invoice
  - [ ] Simular falha temporária no Stark Bank API
  - [ ] Simular webhook de pagamento
  - [ ] Validar retry automático
  - [ ] Validar transfer criada após retry

### 8.4. E2E Test: Transfer Status Updates

**Arquivos:**
- `tests/e2e/test_transfer_status_flow.py`

**Testes:**
- [ ] `test_transfer_processing_to_success`
  - [ ] Criar invoice e simular pagamento
  - [ ] Transfer criada com status="created"
  - [ ] Simular webhook transfer status="processing"
  - [ ] Validar status atualizado
  - [ ] Simular webhook transfer status="success"
  - [ ] Validar status="success" e completed_at preenchido
- [ ] `test_transfer_failed`
  - [ ] Criar invoice e simular pagamento
  - [ ] Transfer criada
  - [ ] Simular webhook transfer status="failed"
  - [ ] Validar error_message salvo
  - [ ] Validar evento `transfer.failed` publicado

### 8.5. E2E Test: Query Endpoints

**Arquivos:**
- `tests/e2e/test_query_endpoints.py`

**Testes:**
- [ ] `test_list_invoices_with_filters`
  - [ ] Criar várias invoices
  - [ ] Testar GET /invoices com filtros
  - [ ] Validar paginação
  - [ ] Validar autenticação
- [ ] `test_get_invoice_by_id`
- [ ] `test_list_transfers_with_filters`
- [ ] `test_get_transfer_by_invoice_id`

### 8.6. E2E Test: Error Scenarios

**Arquivos:**
- `tests/e2e/test_error_scenarios.py`

**Testes:**
- [ ] `test_invalid_webhook_signature`
  - [ ] Simular webhook com assinatura inválida
  - [ ] Validar rejeição
  - [ ] Validar evento `webhook.validation_failed`
- [ ] `test_stark_api_timeout`
  - [ ] Simular timeout no Stark Bank API
  - [ ] Validar retry automático
  - [ ] Validar falha após max attempts
- [ ] `test_database_error_recovery`
  - [ ] Simular erro de database
  - [ ] Validar exception handling
  - [ ] Validar logging de erro

### Entregáveis Fase 8
- ✅ Testes E2E cobrindo fluxos principais
- ✅ Validação de idempotência
- ✅ Validação de retry logic
- ✅ Validação de error handling
- ✅ Cobertura E2E > 70%
- ✅ Documentação de scenarios

### Validação Fase 8
```bash
# Rodar todos E2E tests
pytest tests/e2e/ -v --tb=short

# Rodar com cobertura total
pytest tests/ --cov=src --cov-report=html

# Verificar cobertura
open htmlcov/index.html
```

---

## FASE 9: Documentation & Polish

**Duração Estimada:** 2 dias  
**Objetivo:** Documentar sistema completo e preparar para produção

### 9.1. API Documentation

**Arquivos:**
- `docs/api.md`

**Conteúdo:**
- [ ] Listar todos endpoints
- [ ] Request/Response examples
- [ ] Authentication headers
- [ ] Status codes
- [ ] Error responses
- [ ] Rate limits

### 9.2. README.md

**Arquivo:**
- `README.md`

**Conteúdo:**
- [ ] Descrição do projeto
- [ ] Features implementadas
- [ ] Stack tecnológico
- [ ] Requisitos (Python 3.14)
- [ ] Setup instructions:
  - [ ] Clone repo
  - [ ] Install dependencies
  - [ ] Configure .env
  - [ ] Run migrations
  - [ ] Start app
- [ ] Como testar
- [ ] Deploy instructions (Railway)
- [ ] Licença

### 9.3. Environment Configuration

**Arquivos:**
- `.env.example`
- `docs/configuration.md`

**Conteúdo:**
- [ ] Todas variáveis documentadas
- [ ] Valores default
- [ ] Como obter credenciais Stark Bank
- [ ] Configuração para desenvolvimento vs produção

### 9.4. Deployment Guide

**Arquivos:**
- `docs/deployment.md`
- `Procfile`
- `railway.toml` (ou similar)

**Conteúdo:**
- [ ] Railway setup instructions
- [ ] Environment variables configuration
- [ ] Database persistence
- [ ] Monitoring setup
- [ ] Troubleshooting

### 9.5. Code Quality

**Tarefas:**
- [ ] Rodar linting em todo código: `ruff check src/`
- [ ] Rodar formatting: `ruff format src/`
- [ ] Rodar type checking: `mypy src/` (se configurado)
- [ ] Revisar TODOs e FIXMEs
- [ ] Revisar comentários
- [ ] Remover código morto
- [ ] Validar docstrings

### 9.6. Performance Testing (Opcional)

**Arquivos:**
- `tests/performance/test_load.py`

**Testes:**
- [ ] Load test de criação de invoices
- [ ] Load test de webhooks
- [ ] Verificar tempos de resposta
- [ ] Verificar memory leaks

### Entregáveis Fase 9
- ✅ Documentação completa
- ✅ README detalhado
- ✅ Guia de deployment
- ✅ Código limpo e formatado
- ✅ Sistema pronto para produção

### Validação Fase 9
```bash
# Validar documentação
# Ler README e seguir instruções do zero

# Validar código
ruff check src/
ruff format --check src/

# Validar testes
pytest tests/ --cov=src --cov-report=term

# Validar deploy (Railway)
# Seguir docs/deployment.md
```

---

## FASE 10: Deployment & Monitoring

**Duração Estimada:** 1-2 dias  
**Objetivo:** Deploy em Railway e configurar monitoring

### 10.1. Railway Setup

**Tarefas:**
- [ ] Criar conta Railway
- [ ] Conectar repositório GitHub
- [ ] Configurar variáveis de ambiente
- [ ] Configurar Procfile
- [ ] Configurar volume para database (se disponível)
- [ ] Fazer primeiro deploy
- [ ] Validar aplicação rodando

### 10.2. Environment Variables (Production)

**Configurar no Railway:**
```
STARK_BANK_ENVIRONMENT=sandbox
STARK_BANK_PROJECT_ID=<from-stark-bank>
STARK_BANK_PRIVATE_KEY=<base64-encoded>
API_KEY=<generate-secure-random>
DATABASE_URL=sqlite:///./data/stark_bank.db
LOG_LEVEL=INFO
SCHEDULER_ENABLED=true
SCHEDULER_INTERVAL_HOURS=3
SCHEDULER_DURATION_HOURS=24
```

### 10.3. Database Persistence

**Tarefas:**
- [ ] Configurar volume no Railway (se disponível)
- [ ] Ou migrar para PostgreSQL (Railway oferece free tier)
- [ ] Testar persistência após redeploy
- [ ] Configurar backups (manual ou automático)

### 10.4. Monitoring

**Tarefas:**
- [ ] Configurar Railway dashboard
- [ ] Monitorar logs
- [ ] Monitorar CPU/Memory usage
- [ ] Configurar alertas (se disponível)
- [ ] Testar health check endpoint

### 10.5. Webhook Registration

**Tarefas:**
- [ ] Obter URL do Railway: `https://<app>.railway.app`
- [ ] Registrar webhooks no Stark Bank:
  - [ ] Invoice webhook: `https://<app>.railway.app/webhooks/invoice`
  - [ ] Transfer webhook: `https://<app>.railway.app/webhooks/transfer`
- [ ] Validar recepção de webhooks

### 10.6. Production Testing

**Tarefas:**
- [ ] Aguardar scheduler criar invoices (3h)
- [ ] Monitorar logs de criação
- [ ] Simular pagamento de invoice (Stark Bank sandbox)
- [ ] Validar webhook recebido
- [ ] Validar transfer criada
- [ ] Validar logs completos do fluxo

### Entregáveis Fase 10
- ✅ Aplicação deployed no Railway
- ✅ Database persistindo dados
- ✅ Webhooks registrados e funcionando
- ✅ Monitoring configurado
- ✅ Sistema rodando em produção 24h

### Validação Fase 10
```bash
# Verificar deploy
curl https://<app>.railway.app/health

# Verificar docs
open https://<app>.railway.app/docs

# Monitorar logs
railway logs --tail

# Verificar scheduler
# Aguardar 3h e verificar logs de criação de invoices

# Testar webhook (usar ferramenta Stark Bank)
```

---

## FASE 11: Final Review & Documentation

**Duração Estimada:** 1 dia  
**Objetivo:** Revisar sistema completo e preparar entrega

### 11.1. Code Review

**Tarefas:**
- [ ] Revisar código de cada módulo
- [ ] Validar conformidade com arquitetura
- [ ] Validar tratamento de erros
- [ ] Validar logging
- [ ] Validar testes
- [ ] Validar documentação

### 11.2. Test Coverage Review

**Tarefas:**
- [ ] Rodar cobertura completa
- [ ] Validar > 85% cobertura total
- [ ] Identificar gaps críticos
- [ ] Adicionar testes faltantes

### 11.3. Final Documentation

**Tarefas:**
- [ ] Atualizar [architecture.md](architecture.md) se necessário
- [ ] Atualizar README.md
- [ ] Criar CHANGELOG.md
- [ ] Documentar decisões técnicas importantes
- [ ] Documentar trade-offs e limitações
- [ ] Documentar próximos passos (future improvements)

### 11.4. Demo Preparation

**Tarefas:**
- [ ] Preparar script de demo
- [ ] Preparar screenshots/gifs
- [ ] Preparar video demo (opcional)
- [ ] Preparar apresentação (opcional)

### 11.5. Submission Checklist

**Validar:**
- [ ] ✅ Código no GitHub com README completo
- [ ] ✅ Aplicação deployed e acessível
- [ ] ✅ Webhooks funcionando
- [ ] ✅ Scheduler gerando invoices
- [ ] ✅ Testes com > 85% cobertura
- [ ] ✅ Documentação completa
- [ ] ✅ Logs estruturados
- [ ] ✅ Segurança implementada
- [ ] ✅ Tratamento de erros robusto
- [ ] ✅ Idempotência garantida

### Entregáveis Fase 11
- ✅ Sistema completo revisado
- ✅ Documentação finalizada
- ✅ Demo preparada
- ✅ Pronto para entrega

---

## Timeline Estimado

### Resumo por Fase

| Fase | Descrição | Duração | Dependências |
|------|-----------|---------|--------------|
| 0 | Setup e Fundação | 1 dia | - |
| 1 | Shared Components - Foundation | 2-3 dias | Fase 0 |
| 2 | Stark Bank Integration Layer | 2-3 dias | Fase 1 |
| 3 | Security Layer | 1-2 dias | Fase 1 |
| 4 | Invoices Module | 3-4 dias | Fases 1, 2, 3 |
| 5 | Webhooks Module | 3-4 dias | Fases 1, 3, 4 |
| 6 | Transfers Module | 3-4 dias | Fases 1, 2, 5 |
| 7 | Scheduler & Main App | 2-3 dias | Fases 4, 5, 6 |
| 8 | End-to-End Tests | 2-3 dias | Fase 7 |
| 9 | Documentation & Polish | 2 dias | Fase 8 |
| 10 | Deployment & Monitoring | 1-2 dias | Fase 9 |
| 11 | Final Review | 1 dia | Fase 10 |

**Total Estimado:** 20-30 dias (dependendo da velocidade e experiência)

### Critical Path

```
Fase 0 → Fase 1 → Fase 2 → Fase 4 → Fase 5 → Fase 6 → Fase 7 → Fase 10
         ↓
       Fase 3 (paralelo com Fase 2)
```

### Sprints Sugeridos (Scrum)

**Sprint 1 (1 semana):** Fases 0, 1, 2, 3  
**Sprint 2 (1 semana):** Fases 4, 5  
**Sprint 3 (1 semana):** Fases 6, 7  
**Sprint 4 (1 semana):** Fases 8, 9, 10, 11  

---

## Riscos e Mitigações

### Risco 1: Integração com Stark Bank API

**Risco:** API sandbox instável ou documentação incompleta  
**Mitigação:**
- Implementar retry robusto desde o início
- Mock extensivo em testes
- Contato com suporte Stark Bank se necessário

### Risco 2: Persistência no Railway

**Risco:** Railway free tier não persiste arquivos (SQLite)  
**Mitigação:**
- Opção 1: Usar volume montado
- Opção 2: Migrar para PostgreSQL (Railway oferece free tier)
- Preparar código para ser database-agnostic

### Risco 3: Scheduler em Free Tier

**Risco:** Railway free tier permite apenas 1 processo  
**Mitigação:**
- Rodar scheduler em thread dentro do processo FastAPI
- Código preparado para extrair para processo separado no futuro

### Risco 4: Cobertura de Testes

**Risco:** Dificuldade em atingir 85% cobertura  
**Mitigação:**
- Começar testes desde fase 1
- Test-driven development onde possível
- Focar em código crítico (webhooks, transfers)

### Risco 5: Deadline

**Risco:** Não completar todas fases no prazo  
**Mitigação:**
- Priorizar MVP: Fases 0-7 e 10 são críticas
- Fases 8, 9, 11 podem ser reduzidas se necessário
- Comunicar progresso continuamente

---

## Critérios de Sucesso

### Funcionais

- ✅ Gera invoices automaticamente a cada 3h por 24h
- ✅ Processa webhooks de pagamento corretamente
- ✅ Cria transferências automáticas ao receber pagamento
- ✅ Transferências são idempotentes
- ✅ Processa webhooks de status de transfer
- ✅ APIs de consulta funcionando

### Não-Funcionais

- ✅ Testes com > 85% cobertura
- ✅ Logging estruturado em JSON
- ✅ Retry automático com backoff exponencial
- ✅ Validação de assinaturas digitais
- ✅ Tratamento de erros robusto
- ✅ Documentação completa
- ✅ Código limpo e bem estruturado

### Técnicos

- ✅ Arquitetura modular conforme especificação
- ✅ Event-driven architecture implementada
- ✅ Python 3.14 sem Pydantic
- ✅ FastAPI + SQLite
- ✅ Deploy funcionando no Railway
- ✅ Webhooks registrados e recebendo eventos

---

## Próximos Passos após v1.0

### Short Term (v1.1)

- Circuit breaker pattern
- PostgreSQL como opção de banco
- Metrics com Prometheus
- Rate limiting em endpoints
- Dashboard de monitoramento
- Retry manual de operações falhadas

### Medium Term (v2.0)

- Microserviços (separar módulos)
- Message queue (RabbitMQ/SQS)
- Distributed tracing
- Autenticação OAuth2
- Multi-tenant support
- API versioning

### Long Term (v3.0)

- Kubernetes deployment
- Auto-scaling
- Multi-region
- Real-time dashboard
- Analytics e BI
- Machine learning para detecção de fraudes

---

## Conclusão

Este plano de implementação gradual garante:

1. **Progresso Incremental:** Cada fase entrega valor e pode ser validada
2. **Redução de Riscos:** Problemas são detectados cedo
3. **Qualidade:** Testes acompanham implementação
4. **Flexibilidade:** Fases podem ser ajustadas conforme necessário
5. **Documentação:** Sistema sempre documentado

**Próximo Passo:** Iniciar Fase 0 - Setup e Fundação

---

**Documento vivo - atualizar conforme implementação progride**
