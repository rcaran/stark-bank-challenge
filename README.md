# Stark Bank Challenge

Projeto de integração automatizada com Stark Bank para geração de invoices e transferências, desenvolvido como parte do processo seletivo.

## Estrutura do Projeto

O projeto segue uma arquitetura modular baseada em eventos, organizada da seguinte forma:

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
│   │   └── security/      # Segurança e validação
│   │
│   ├── config/            # Configurações globais
│   ├── main.py            # Entry point da API (FastAPI)
│   └── scheduler.py       # Entry point do Scheduler
│
├── tests/                 # Testes automatizados
├── docs/                  # Documentação detalhada
└── migrations/            # Migrações de banco de dados
```

## Setup do Ambiente

### Pré-requisitos
- Python 3.14+
- Gerenciador de dependências (Rye ou Poetry recomendado, ou pip padrão)

### Instalação

1. Clone o repositório:
```bash
git clone https://github.com/your-user/stark-bank-challenge.git
cd stark-bank-challenge
```

2. Configure o ambiente virtual e instale dependências:

**Usando pip (padrão):**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou .venv\Scripts\activate  # Windows
pip install -e .[dev]
```

**Usando Rye:**
```bash
rye sync
```

**Usando Poetry:**
```bash
poetry install
```

3. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite o arquivo .env com suas credenciais do Stark Bank
```

## Variáveis de Ambiente

As principais variáveis de configuração em `.env` são:

- `APP_ENV`: Ambiente (development, production, test)
- `STARKBANK_PROJECT_ID`: ID do projeto no Stark Bank
- `STARKBANK_PRIVATE_KEY_CONTENT`: Conteúdo da chave privada ECDSA
- `STARKBANK_ENVIRONMENT`: `sandbox` ou `production`
- `SCHEDULER_INTERVAL_HOURS`: Intervalo de execução do job de invoices (padrão: 3h)
- `INVOICE_GENERATION_MIN/MAX`: Faixa de quantidade de invoices por execução

## Executando o Projeto

### API Server
```bash
uvicorn src.main:app --reload --port 8000
```

### Scheduler
(O scheduler pode rodar separadamente ou como background task, verificar implementação futura)
```bash
python src/scheduler.py
```

## Desenvolvimento

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

### Testes
O projeto utiliza `pytest`.

```bash
# Executar todos os testes
pytest

# Executar com cobertura
pytest --cov=src

# Executar testes unitários apenas
pytest tests/unit
```

## Documentação Adicional
- [Arquitetura](docs/architecture.md)
- [Plano de Implementação](docs/implementation-plan.md)
- [Desafio](docs/challenge.md)
