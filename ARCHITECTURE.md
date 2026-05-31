# EditalFácil — Architecture Decision Record

## Padrão geral

**Modular Monolith** com **Task Queue** assíncrona, organizado em **Layered Architecture** internamente.

Escolhido em detrimento de microsserviços: evita complexidade operacional prematura. Referências que seguiram esse caminho: Shopify, Basecamp, GitHub.

---

## Diagrama de componentes

```
┌─────────────────────────────────────────────────────┐
│                    CLIENTE                          │
│         Browser (HTML + Bootstrap / HTMX)           │
└────────────────────┬────────────────────────────────┘
                     │ HTTPS
┌────────────────────▼────────────────────────────────┐
│                  NGINX                              │
│         Reverse proxy + SSL termination             │
└────────┬───────────────────────────┬────────────────┘
         │                           │
┌────────▼────────┐       ┌──────────▼──────────┐
│   API (Flask)   │       │   Static Files      │
│   stateless     │       │   (CSS, JS)         │
└────────┬────────┘       └─────────────────────┘
         │
┌────────▼────────────────────────────────────────────┐
│                 SERVICE LAYER                       │
│  AuthService  │  EditalService  │  UserService     │
└────┬──────────┴────────┬────────┴──────────────────┘
     │                   │
     │          ┌─────────▼──────────┐
     │          │   FILA (Redis)     │
     │          │   Celery Queue     │
     │          └─────────┬──────────┘
     │                    │
     │          ┌─────────▼──────────┐
     │          │  WORKER (Celery)   │
     │          │  pdfplumber + LLM  │
     │          └─────────┬──────────┘
     │                    │
┌────▼────────────────────▼───────────────────────────┐
│                  DATA LAYER                         │
│   PostgreSQL        │   MinIO / S3   │   Redis      │
│   (dados)           │   (PDFs)       │   (cache)    │
└─────────────────────────────────────────────────────┘
```

---

## Decisões de tecnologia

### Backend
- **Python 3.12 + Flask** — leveza, ecossistema maduro para data/PDF processing
- **Celery** — task queue para processar PDFs de forma assíncrona (evita timeout)
- **Redis** — broker da fila Celery e cache de resultados

### Banco de dados
- **PostgreSQL** (produção) — suporta escritas concorrentes, full-text search, JSON columns
- **SQLite** (MVP/desenvolvimento) — sem infraestrutura, substituto direto via SQLAlchemy

### Armazenamento de arquivos
- **MinIO** (dev/staging) — S3 self-hosted, mesma API
- **AWS S3** (produção) — object storage gerenciado
- PDFs nunca ficam no disco do servidor

### Extração de PDF
- **pdfplumber** — escolhido sobre PyPDF2/pymupdf por preservar layout, extrair tabelas nativamente e ter manutenção ativa
- **LLM (Anthropic Claude via LiteLLM)** — extração 100% via LLM; cada órgão publica o edital em formato diferente, tornando regex/tabelas inviáveis para cobertura geral

### Frontend
- **HTML + Bootstrap** no MVP
- **HTMX** como evolução natural sem trocar de framework

### Infraestrutura
- **Nginx** — reverse proxy, SSL, rate limiting, serve estáticos
- **Docker + Docker Compose** — ambiente reproduzível dev/prod
- **Alembic** — migrations de banco

---

## Fluxo de processamento (happy path)

```
1. Usuário faz upload do PDF
2. API salva arquivo no MinIO → retorna job_id + status "processing"
3. API enfileira task no Celery via Redis
4. Worker processa: pdfplumber extrai texto → LLM estrutura os dados
5. Worker salva resultado estruturado no PostgreSQL
6. Frontend faz polling em GET /editais/{job_id}/status
7. Quando status = "done", exibe resumo estruturado
```

---

## Campos extraídos (MVP)

- Cargo(s)
- Salário(s)
- Escolaridade exigida
- Quantidade de vagas
- Cidade / Estado
- Data da prova
- Período de inscrição

---

## Evolução MVP → Produção

| Componente     | MVP              | Produção              |
|----------------|------------------|-----------------------|
| Banco          | SQLite           | PostgreSQL            |
| Fila           | Síncrono         | Celery + Redis        |
| Storage        | Disco local      | MinIO / S3            |
| Auth           | Sem auth         | JWT + refresh token   |
| Workers        | Mesma thread     | Containers separados  |
| Proxy          | Flask direto     | Nginx                 |

A estrutura de pastas, interfaces dos services e contratos das rotas seguem o padrão de produção desde o início — apenas a implementação interna muda.

---

## Estrutura de pastas

```
edital_facil/
├── api/
│   ├── __init__.py
│   ├── config.py               # settings por ambiente (dev/prod)
│   ├── routes/
│   │   ├── auth.py
│   │   ├── editais.py
│   │   └── users.py
│   ├── services/
│   │   ├── edital_service.py
│   │   ├── llm.py                  # cliente LiteLLM (provider-agnostic)
│   │   ├── storage_service.py
│   │   └── auth_service.py
│   ├── workers/
│   │   └── tasks.py            # Celery tasks
│   ├── models/
│   │   ├── edital.py
│   │   ├── cargo.py                # um registro por cargo/habilitação
│   │   └── user.py
│   └── extractors/
│       └── pdf_extractor.py    # pdfplumber (texto) + LLM (estruturação)
├── frontend/
├── migrations/                 # Alembic
├── tests/
│   ├── unit/
│   └── integration/
├── infra/
│   ├── nginx/nginx.conf
│   ├── docker-compose.yml
│   └── docker-compose.prod.yml
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── .env.example
├── Dockerfile
├── ARCHITECTURE.md
└── README.md
```

---

## Padrões de código

### Linter e formatter: Ruff

Configurado em `pyproject.toml`. Ruff substitui flake8, isort e black em uma única ferramenta.

```bash
.venv/bin/ruff check .          # verifica violações
.venv/bin/ruff check . --fix    # corrige o que é automático
.venv/bin/ruff format .         # formata o código
```

**Regras ativas:**

| Prefixo | Conjunto | O que verifica |
|---------|----------|----------------|
| `E/W`   | pycodestyle | estilo PEP 8 |
| `F`     | pyflakes | imports não usados, variáveis indefinidas |
| `I`     | isort | ordem de imports |
| `N`     | pep8-naming | convenção de nomes |
| `D`     | pydocstyle | presença e formato de docstrings |
| `UP`    | pyupgrade | sintaxe moderna (Python 3.12+) |
| `B`     | flake8-bugbear | bugs comuns e más práticas |
| `S`     | flake8-bandit | vulnerabilidades de segurança |
| `RUF`   | ruff-specific | regras próprias do Ruff |

**Exceções documentadas:**
- `tests/**`: ignora `S101` (assert) e `D` (docstrings não obrigatórias em testes)
- `api/extractors/**`: ignora `RUF001` (EN DASH em regex é intencional — PDFs governamentais usam esse caractere como separador)

### Docstrings: Google Style

Toda função pública, classe e método público deve ter docstring. Funções privadas (prefixo `_`) são opcionais.

```python
def extrair_campos(filepath: str) -> dict:
    """Extrai os campos estruturados de um edital de concurso público.

    Args:
        filepath: caminho para o arquivo PDF do edital.

    Returns:
        Dicionário com os campos extraídos. Valor None quando não encontrado.
    """
```

Regras ignoradas globalmente: `D100/D104` (docstring de módulo/pacote), `D203/D213` (conflito de estilos).

### Commits: Conventional Commits

Formato: `<tipo>(<escopo opcional>): <descrição>`

| Tipo | Quando usar |
|------|-------------|
| `feat` | nova funcionalidade |
| `fix` | correção de bug |
| `chore` | manutenção, deps, config |
| `refactor` | refatoração sem mudança de comportamento |
| `test` | adição ou correção de testes |
| `docs` | documentação |

Exemplos:
```
feat(extractor): adicionar extração de data da prova
fix(routes): retornar 400 quando PDF está corrompido
chore: atualizar pdfplumber para 0.11.5
```

### Formatação geral

- **Aspas**: duplas (`"`)
- **Indentação**: 4 espaços
- **Line length**: 100 caracteres
- **Line endings**: LF (`\n`)
- **Target**: Python 3.12+

---

## CI/CD

### GitHub Actions

Workflow em `.github/workflows/lint.yml` — roda em todo push e PR para `master`.

**Jobs:**
- `ruff check .` — verifica violações de lint
- `ruff format --check .` — verifica formatação

Usa `astral-sh/ruff-action@v3` (sem instalar dependências Python, execução rápida).
Node.js 24 habilitado via `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true`.

**Regra:** o pipeline deve estar verde antes de qualquer merge. Nunca fazer push com `ruff` falhando localmente.

---

## O que não foi decidido ainda

- Modelo de precificação / multi-tenancy
- Autenticação social (Google OAuth) vs email/senha
- Estratégia de retry para processamento com falha
