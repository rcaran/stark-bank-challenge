# Stark Bank Challenge

Sistema automatizado de gestão de invoices e transferências integrado com a API do Stark Bank. O sistema gera invoices periodicamente (a cada 3 horas), processa webhooks de pagamento e executa transferências automaticamente ao receber pagamentos.

Desenvolvido como parte do processo seletivo do Stark Bank, demonstrando capacidade de integração com APIs externas, arquitetura orientada a eventos, segurança e tratamento robusto de erros.

## 🚀 Features Implementadas

- ✅ **Geração Automática de Invoices**: Scheduler que cria 8-12 invoices a cada 3 horas durante 24h
- ✅ **Validação de Dados**: Geração de CPF/CNPJ válidos com distribuição 70/30
- ✅ **Webhook Processing**: Recepção e processamento seguro de webhooks do Stark Bank
- ✅ **Validação de Assinatura Digital**: Verificação ECDSA de webhooks para garantir autenticidade
- ✅ **Transferências Automáticas**: Criação automática de transfers ao receber pagamentos de invoices
- ✅ **Retry Logic**: Sistema de retry exponencial para chamadas à API do Stark Bank
- ✅ **Idempotência**: Garantia de não duplicação de transferências
- ✅ **Event Bus**: Arquitetura orientada a eventos para desacoplamento de módulos
- ✅ **API RESTful**: Endpoints protegidos com API Key para consulta de invoices e transfers
- ✅ **Logging Estruturado**: Logs detalhados em formato JSON para monitoramento
- ✅ **Health Check**: Endpoint de verificação de saúde da aplicação
- ✅ **Persistência**: Banco de dados SQLite com migrations automáticas
- ✅ **Testes Abrangentes**: Cobertura > 85% (unitários, integração e E2E)

## 🛠️ Stack Tecnológico

- **Python 3.14+**: Linguagem principal
- **FastAPI**: Framework web assíncrono para APIs
- **Stark Bank SDK**: Integração oficial com Stark Bank
- **SQLite**: Banco de dados (fácil migração para PostgreSQL)
- **APScheduler**: Agendamento de tarefas periódicas
- **Pydantic**: Validação de dados e settings
- **pytest**: Framework de testes
- **Ruff**: Linting e formatação de código
- **Uvicorn**: Servidor ASGI de alta performance

## 📂 Estrutura do Projeto

O projeto segue uma arquitetura modular baseada em eventos:

```
stark-bank-challenge/
├── src/
│   ├── modules/           # Módulos de domínio
│   │   ├── invoices/      # Geração e gestão de invoices
│   │   ├── webhooks/      # Processamento de webhooks
│   │   └── transfers/     # Execução de transferências
│   │
│   ├── shared/            # Componentes compartilhados
│   │   ├── database/      # Camada de dados
│   │   ├── events/        # Event Bus
│   │   ├── stark/         # Integração com Stark Bank
│   │   ├── security/      # Segurança e validação
│   │   └── utils/         # Utilitários
│   │
│   ├── config/            # Configurações globais
│   ├── main.py            # Entry point da API (FastAPI)
│   └── scheduler.py       # Scheduler de invoices
│
├── tests/                 # Testes automatizados
│   ├── unit/              # Testes unitários
│   ├── integration/       # Testes de integração
│   └── e2e/               # Testes end-to-end
│
├── docs/                  # Documentação detalhada
└── migrations/            # Migrações de banco de dados
```

## 📋 Requisitos

- **Python 3.14+** (ou 3.11+)
- Conta no [Stark Bank](https://starkbank.com) (ambiente sandbox)
- Git

## 🔧 Setup do Ambiente

### 1. Clone o Repositório

```bash
git clone https://github.com/your-username/stark-bank-challenge.git
cd stark-bank-challenge
```

### 2. Instale as Dependências

**Usando pip (padrão):**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
pip install -e .[dev]
```

**Usando Rye (recomendado):**
```bash
rye sync
```

**Usando Poetry:**
```bash
poetry install
```

### 3. Configure as Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais:

```env
# Application
APP_ENV=development
LOG_LEVEL=INFO

# Stark Bank Credentials
STARK_BANK_PROJECT_ID=seu-project-id-aqui
STARK_BANK_PRIVATE_KEY=-----BEGIN EC PRIVATE KEY-----\nSua\nChave\nPrivada\nAqui\n-----END EC PRIVATE KEY-----
STARK_BANK_ENVIRONMENT=sandbox

# API Security
API_KEY=dev-key-insecure-change-in-production

# Database
DATABASE_PATH=./data/stark_bank.db

# Scheduler
SCHEDULER_ENABLED=true
SCHEDULER_INTERVAL_HOURS=3
SCHEDULER_DURATION_HOURS=24

# Invoice Generation
INVOICE_MIN_COUNT=8
INVOICE_MAX_COUNT=12
INVOICE_MIN_AMOUNT=100
INVOICE_MAX_AMOUNT=10000
INVOICE_DUE_DAYS_MIN=1
INVOICE_DUE_DAYS_MAX=7
```

**Como obter as credenciais do Stark Bank:**
1. Acesse [Stark Bank Sandbox](https://web.sandbox.starkbank.com)
2. Crie uma conta de desenvolvedor
3. Gere um par de chaves ECDSA (Elliptic Curve)
4. Registre a chave pública no painel do Stark Bank
5. Copie o Project ID e a chave privada para o `.env`

### 4. Execute as Migrações do Banco de Dados

As migrações rodam automaticamente ao iniciar a aplicação, mas você pode executá-las manualmente:

```bash
python -c "from src.shared.database.migrations import run_migrations; run_migrations()"
```

### 5. Inicie a Aplicação

**Modo Development (com auto-reload):**
```bash
uvicorn src.main:app --reload --port 8000
```

**Modo Production:**
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

A aplicação estará disponível em: `http://localhost:8000`

- **API Docs (Swagger):** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/health`

### 6. Configure os Webhooks no Stark Bank

Para receber notificações de pagamento:

1. Acesse o painel do Stark Bank
2. Configure os seguintes webhooks:
   - **Invoice:** `https://sua-url.railway.app/webhooks/invoice`
   - **Transfer:** `https://sua-url.railway.app/webhooks/transfer`

## 🧪 Como Testar

### Executar Todos os Testes

```bash
pytest
```

### Testes por Categoria

```bash
# Apenas testes unitários
pytest tests/unit -v

# Apenas testes de integração
pytest tests/integration -v

# Apenas testes E2E
pytest tests/e2e -v
```

### Testes com Cobertura

```bash
# Gerar relatório de cobertura
pytest --cov=src --cov-report=html --cov-report=term

# Ver relatório HTML
# Abra: htmlcov/index.html no navegador
```

### Testes Específicos

```bash
# Testar módulo específico
pytest tests/unit/modules/invoices/ -v

# Testar arquivo específico
pytest tests/unit/modules/invoices/test_service.py -v

# Testar função específica
pytest tests/unit/modules/invoices/test_service.py::test_create_invoice_success -v
```

### Testar Fluxo Completo (Manual)

1. **Criar Invoice:**
```bash
curl -X POST http://localhost:8000/invoices \
  -H "X-API-Key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1000,
    "tax_id": "012.345.678-90",
    "name": "João Silva",
    "due": "2026-02-20"
  }'
```

2. **Listar Invoices:**
```bash
curl -X GET "http://localhost:8000/invoices?status=created&limit=10" \
  -H "X-API-Key: dev-key"
```

3. **Simular Webhook de Pagamento** (use ferramentas do Stark Bank ou Postman)

4. **Verificar Transfer Criada:**
```bash
curl -X GET http://localhost:8000/transfers \
  -H "X-API-Key: dev-key"
```

## 🚀 Deploy (Railway)

> 📖 **Para instruções detalhadas de deployment**, consulte o [Guia de Deployment](docs/deployment.md), que inclui:
> - Configuração passo a passo do Railway
> - Configuração de variáveis de ambiente
> - Persistência de banco de dados
> - Monitoramento e troubleshooting
> - Deploy alternativo (Heroku, Render, Docker, DigitalOcean)

### Pré-requisitos

- Conta no [Railway](https://railway.app)
- Projeto conectado ao GitHub

### Passos para Deploy

1. **Crie um novo projeto no Railway:**
   - Clique em "New Project"
   - Selecione "Deploy from GitHub repo"
   - Escolha o repositório `stark-bank-challenge`

2. **Configure as Variáveis de Ambiente:**
   
   No Railway, vá em "Variables" e adicione:
   ```
   APP_ENV=production
   LOG_LEVEL=INFO
   STARK_BANK_PROJECT_ID=<seu-project-id>
   STARK_BANK_PRIVATE_KEY=<sua-chave-privada>
   STARK_BANK_ENVIRONMENT=sandbox
   API_KEY=<gere-uma-chave-forte>
   DATABASE_PATH=/app/data/stark_bank.db
   SCHEDULER_ENABLED=true
   SCHEDULER_INTERVAL_HOURS=3
   SCHEDULER_DURATION_HOURS=24
   ```

3. **Configure o Comando de Start:**
   
   No Railway, em "Settings" > "Deploy", configure:
   ```
   uvicorn src.main:app --host 0.0.0.0 --port $PORT
   ```

4. **Configure Volume para Persistência (Opcional):**
   - Railway oferece volumes persistentes
   - Monte em `/app/data` para manter o banco SQLite
   - Ou migre para PostgreSQL (Railway oferece PostgreSQL gratuito)

5. **Deploy:**
   - Faça commit no GitHub
   - Railway fará deploy automaticamente

6. **Configure os Webhooks:**
   - Após deploy, copie a URL do Railway: `https://seu-app.railway.app`
   - Configure no Stark Bank:
     - Invoice: `https://seu-app.railway.app/webhooks/invoice`
     - Transfer: `https://seu-app.railway.app/webhooks/transfer`

7. **Monitore:**
   - Use Railway Logs para monitorar
   - Verifique Health Check: `https://seu-app.railway.app/health`

### Alternativa: Deploy com Docker

```bash
# Dockerfile já configurado no projeto
docker build -t stark-bank-challenge .
docker run -p 8000:8000 --env-file .env stark-bank-challenge
```

## 💻 Desenvolvimento

### Linting e Formatação
O projeto utiliza `ruff` para linting e formatação.

```bash
# Check linting
ruff check src/

# Auto-fix linting
ruff check src/ --fix

# Format code
ruff format src/
```

### Scripts Disponíveis (Windows)

```bash
# Formatar código
.\scripts\format.bat

# Executar linter
.\scripts\lint.bat

# Executar testes
.\scripts\test.bat
```

## 📚 Documentação Adicional

- [Arquitetura](docs/architecture.md) - Decisões arquiteturais e padrões utilizados
- [API](docs/api.md) - Documentação completa da API REST
- [Plano de Implementação](docs/implementation-plan.md) - Plano detalhado de desenvolvimento
- [Desafio Original](docs/challenge.md) - Especificação do desafio

## 📊 Arquitetura

O sistema utiliza **arquitetura orientada a eventos** com os seguintes componentes principais:

- **Event Bus**: Desacopla módulos via publish/subscribe
- **Repository Pattern**: Abstração de acesso a dados
- **Service Layer**: Lógica de negócio
- **API Layer**: Endpoints REST com FastAPI

### Fluxo Principal

1. **Scheduler** gera invoices a cada 3h
2. Invoices são criadas na **Stark Bank API**
3. Quando paga, **webhook** notifica o sistema
4. Sistema valida assinatura ECDSA
5. **Event Bus** publica evento `invoice.paid`
6. **Transfer Handler** escuta evento e cria transfer
7. Transfer é executada na Stark Bank
8. Webhooks notificam status da transfer

## 🔒 Segurança

- Validação de assinatura digital ECDSA em todos webhooks
- API Key authentication para endpoints privados
- Validação de dados de entrada com Pydantic
- Logging de todas operações sensíveis
- Secrets via variáveis de ambiente

## 🧰 Tecnologias e Padrões

- **Clean Architecture**: Separação de camadas
- **SOLID Principles**: Código manutenível e testável
- **Dependency Injection**: Desacoplamento de dependências
- **Repository Pattern**: Abstração de persistência
- **Event-Driven Architecture**: Comunicação assíncrona entre módulos
- **Retry Pattern**: Resiliência em chamadas externas
- **Idempotency**: Prevenção de duplicação

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👤 Autor

Desenvolvido como parte do processo seletivo do Stark Bank.

---

**Nota**: Este projeto utiliza o ambiente **sandbox** do Stark Bank. Para uso em produção, ajuste as configurações apropriadamente.
