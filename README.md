# EditalFácil

Micro-SaaS para processar editais de concurso público em PDF e extrair informações estruturadas.

## O que extrai

- Cargo(s)
- Salário(s)
- Escolaridade exigida
- Quantidade de vagas
- Cidade / Estado
- Data da prova
- Período de inscrição

## Rodando localmente

```bash
# 1. Criar ambiente virtual e instalar dependências
python3 -m venv .venv
.venv/bin/pip install -r requirements/dev.txt

# 2. Copiar variáveis de ambiente
cp .env.example .env

# 3. Iniciar a aplicação
.venv/bin/python run.py
```

Acesse em http://localhost:5000.

## Testando o extrator isolado

```bash
.venv/bin/python -m api.extractors.pdf_extractor caminho/para/edital.pdf
```

## Qualidade de código

```bash
.venv/bin/ruff format .     # formata
.venv/bin/ruff check .      # verifica lint
```

O CI valida automaticamente em todo push para `master`. Consulte [ARCHITECTURE.md](ARCHITECTURE.md) para decisões de arquitetura e padrões de código.

## Stack

- **Backend**: Python 3.12 + Flask
- **Extração de PDF**: pdfplumber
- **Banco**: SQLite (dev) / PostgreSQL (prod)
- **Fila**: Celery + Redis
- **Storage**: MinIO (dev) / S3 (prod)
- **Infra**: Docker + Nginx
