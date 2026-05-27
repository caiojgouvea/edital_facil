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
- **LLM (fallback)** — para editais com estrutura não-padrão onde regex falha

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
4. Worker processa: pdfplumber → regex → LLM (se fallback necessário)
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
│   │   ├── storage_service.py
│   │   └── auth_service.py
│   ├── workers/
│   │   └── tasks.py            # Celery tasks
│   ├── models/
│   │   ├── edital.py
│   │   └── user.py
│   └── extractors/
│       ├── pdf_extractor.py    # pdfplumber + regex
│       └── llm_extractor.py   # fallback LLM
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

## O que não foi decidido ainda

- Modelo de precificação / multi-tenancy
- Autenticação social (Google OAuth) vs email/senha
- Modelo de LLM para fallback (GPT-4o, Claude, Gemini)
- Estratégia de retry para processamento com falha
