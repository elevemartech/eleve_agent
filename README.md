# eleve-agent

Agente de IA para comunicação escola-família via WhatsApp.

**FastAPI + LangGraph + OpenAI | Python 3.12 | Poetry**

---

## Setup rápido

```bash
# 1. Clonar e entrar na pasta
git clone <repo> eleve-agent
cd eleve-agent

# 2. Instalar dependências
poetry install

# 3. Configurar variáveis
cp .env.example .env
# Editar .env com as credenciais reais

# 4. Subir Redis
docker-compose up redis -d

# 5. Rodar o servidor
poetry run uvicorn main:app --reload --port 8080

# 6. Testar
poetry run pytest tests/ -v
```

## Docker (produção)

```bash
docker-compose up --build
```

## Variáveis obrigatórias

| Variável | Descrição |
|---|---|
| `DJANGO_API_URL` | URL da Eleve API |
| `SYSTEM_SA_TOKEN` | ServiceAccount do sistema |
| `OPENAI_API_KEY` | Chave OpenAI |
| `REDIS_URL` | URL do Redis |
| `UAZAPI_BASE_URL` | URL da instância UazAPI |

## Arquitetura

Ver [CLAUDE.md](CLAUDE.md) para documentação completa de arquitetura,
agentes, tools e convenções de código.
