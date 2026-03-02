# CLAUDE.md — eleve-agent

Contexto permanente para o Claude Code. Leia inteiro antes de qualquer tarefa.

---

## O que é este projeto

Microserviço Python (**FastAPI + LangGraph**) que processa mensagens WhatsApp
para a plataforma **Eleve** — SaaS multi-tenant de gestão escolar.

Substitui o n8n como orquestrador do agente de IA.
**Sem banco de dados próprio** — toda persistência vai para a Eleve API (Django).

## Repositório irmão

API Django em `../eleve-api`. Leia os arquivos diretamente quando precisar
entender endpoints, serializers ou models. Não suponha — leia o arquivo real.

Caminhos úteis:
```
../eleve-api/apps/contacts/views/student_guardian_views.py
../eleve-api/apps/contacts/views/guardian_viewset.py
../eleve-api/apps/contacts/serializers/invoice_serializers.py
../eleve-api/apps/attendances/views/session_viewset.py
../eleve-api/apps/attendances/services/session_service.py
../eleve-api/apps/requests/choices.py
../eleve-api/apps/secretary/views.py
../eleve-api/apps/management/models.py
../eleve-api/apps/evaluations/models.py
../eleve-api/config/urls.py
```

## Stack

```
FastAPI + uvicorn    → webhook e orquestração
LangGraph           → StateGraph com roteamento condicional
LangChain + OpenAI  → LLM (gpt-4o-mini), vision (gpt-4o), audio (whisper-1)
Redis               → cache school_resolver (1h) + message batching (3s)
httpx               → cliente HTTP assíncrono para a Eleve API
Poetry              → gerenciamento de dependências e lock file
```

## Autenticação na Eleve API

Cada escola tem um **ServiceAccount** com token `sa_live_{school_id}_{hex}`.
Todas as chamadas usam esse token — isolamento multi-tenant automático.

```python
headers = {"Authorization": f"Token {sa_token}"}
```

**Nunca use token de usuário humano. Sempre ServiceAccount.**

## Fluxo completo de uma mensagem

```
WhatsApp → POST /webhook (main.py)
  → school_resolver   identifica escola pelo messaging_token (cache Redis 1h)
  → message_batcher   agrupa mensagens sequenciais (debounce 3s)
  → media_handler     Whisper (áudio) ou GPT-4o Vision (imagem) → texto
  → session_manager   POST /attendances/sessions/webhook/ → busca ou cria sessão
  → AgentState        monta estado com histórico e metadata da sessão
  → StateGraph        router → agente → tool calls
  → session_manager   salva mensagem do agente + metadata atualizado
  → provider          envia resposta ao WhatsApp
```

## AgentState

```python
class AgentState(TypedDict, total=False):
    input: str              # texto normalizado (áudio/imagem já convertidos)
    phone: str
    contact_name: str
    school_id: str
    school_name: str
    sa_token: str           # Token do ServiceAccount
    session_id: str
    instance_token: str
    history: list[dict]     # Últimas 10 msgs [{role, content}]
    guardian_context: dict | None  # {found, guardian_id, guardian_name, students}
    current_agent: str      # Agente ativo
    current_step: int       # Passo do fluxo multi-etapas
    keep_flow: bool
    collected_data: dict
    response: str
```

### Persistência entre turnos

`current_agent`, `current_step`, `collected_data` e `guardian_context`
são salvos no `metadata` da `ServiceSession` ao final de cada mensagem.
No início da próxima mensagem, `main.py` carrega esse metadata.

## Agentes

```
router → greeting | financial | faq | secretary | enrollment |
         protocol | announcement | human | closing
```

**Router** retorna: `{"agent": "financial", "keep_flow": false, "confidence": 0.94}`

`keep_flow=true` → usuário respondendo pergunta do agente atual (mantém)
`keep_flow=false` → novo assunto ou sessão nova (roteia)

## Tools — Status

### ✅ Prontas

| Tool | Arquivo | Endpoint |
|------|---------|----------|
| `search_faq` | tools/search_faq.py | GET /api/v1/faqs/ |
| `create_request` | tools/create_request.py | POST /api/v1/requests/ |
| `create_enrollment` | tools/create_enrollment.py | POST /api/v1/secretary/enrollments/ |
| `create_ticket` | tools/create_ticket.py | POST /api/v1/tickets/ |
| `get_guardian_by_phone` | tools/get_guardian_by_phone.py | GET /api/v1/contacts/students/guardians/ |
| `get_invoices` | tools/get_invoices.py | GET /api/v1/contacts/guardians/{id}/invoices/ |
| `get_unread_announcements` | tools/get_unread_announcements.py | GET /api/v1/management/announcements/ |
| `get_requests_by_guardian` | tools/get_requests_by_guardian.py | GET /api/v1/requests/ |
| `get_request_by_protocol` | tools/get_request_by_protocol.py | GET /api/v1/requests/?search= |
| `create_evaluation` | tools/create_evaluation.py | POST /api/v1/evaluations/ |

### 🔧 A ajustar conforme a API real

Ao implementar ou corrigir uma tool, sempre leia o serializer/view correspondente
em `../eleve-api` para verificar campos exatos antes de escrever.

## Endpoints Eleve API — referência rápida

```
# Sessões
POST /api/v1/attendances/sessions/webhook/          → find_or_create + adiciona msg
GET  /api/v1/attendances/sessions/{id}/             → detalhes com metadata
POST /api/v1/attendances/sessions/{id}/message/     → adiciona mensagem
POST /api/v1/attendances/sessions/{id}/action/      → registra ação do agente
POST /api/v1/attendances/sessions/{id}/close/       → encerra (reason, summary)
POST /api/v1/attendances/sessions/{id}/escalate/    → escala para humano
PATCH /api/v1/attendances/sessions/{id}/            → atualiza metadata

# Responsáveis
GET  /api/v1/contacts/students/guardians/           → ?search={nome_ou_fone}
GET  /api/v1/contacts/guardians/{id}/invoices/      → boletos (?situacao=ABE)

# Solicitações
POST /api/v1/requests/                              → cria (gera card automático)
GET  /api/v1/requests/                              → ?siga_user_id= ou ?search=

# Matrículas
POST /api/v1/secretary/enrollments/                 → registra interesse

# FAQs e Tickets
GET  /api/v1/faqs/                                  → ?search=&is_active=true
POST /api/v1/tickets/                               → cria ticket

# Comunicados
GET  /api/v1/management/announcements/              → ?type=urgente&published=true
POST /api/v1/management/announcements/{id}/mark_read/

# Avaliações
POST /api/v1/evaluations/                           → NPS {name, phone, rating, channel}

# Escalação
POST /api/v1/attendances/sessions/{id}/escalate/    → {reason}
```

## Tipos de solicitação

```python
# apps/requests/choices.py
'boleto_2via' | 'declaracao' | 'historico' |   # sem aprovação obrigatória
'transferencia' | 'rematricula' | 'cancelamento' | 'negociacao' | 'outros'
```

## Regras de negócio críticas

1. **Nunca negociar dívida** → detectar → `escalate_session` imediatamente
2. **Nunca inventar informações** → não está no FAQ → criar ticket
3. **Uma pergunta por vez** em fluxos multi-passo (matrícula, secretaria)
4. **Corte de série**: 31/03 do ano letivo — sugerir série correta se não bater
5. **Escalação automática**: linguagem forte, 3+ tentativas sem resolução, pedido explícito
6. **NPS sempre no encerramento** → salvar via `create_evaluation` na API
7. **Nunca logar** tokens, CPFs ou dados pessoais completos

## Convenção de tool

```python
@tool
async def nome_da_tool(param: str, sa_token: str, **kwargs) -> str:
    """Descrição em uma linha — o LLM usa isso para decidir quando chamar."""
    client = DjangoAPIClient(token=sa_token)
    try:
        result = await client.get("/api/v1/endpoint/", params={...})
        return "Resultado formatado como texto"
    except Exception as e:
        return f"Mensagem de fallback amigável: {e}"
```

## Como rodar

```bash
# Dependências
poetry install

# Variáveis
cp .env.example .env   # editar com valores reais

# Redis
docker-compose up redis -d

# Servidor
poetry run uvicorn main:app --reload --port 8080

# Testes
poetry run pytest tests/ -v
```

## Estrutura de arquivos

```
eleve-agent/
├── main.py                         ← Webhook + orquestração
├── CLAUDE.md                       ← Este arquivo
├── pyproject.toml                  ← Poetry
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── core/
│   ├── settings.py
│   ├── api_client.py
│   ├── school_resolver.py
│   ├── session_manager.py
│   ├── message_batcher.py
│   ├── audio_processor.py
│   ├── image_processor.py
│   ├── media_handler.py
│   └── whatsapp/
│       ├── base.py
│       ├── uazapi.py
│       ├── meta.py
│       └── factory.py
├── agents/
│   ├── state.py
│   ├── graph.py
│   ├── router.py
│   ├── greeting.py
│   ├── financial.py
│   ├── faq.py
│   ├── secretary.py
│   ├── enrollment.py
│   ├── protocol.py
│   ├── announcement.py
│   ├── human.py
│   └── closing.py
├── tools/
│   ├── search_faq.py
│   ├── create_request.py
│   ├── create_enrollment.py
│   ├── create_ticket.py
│   ├── get_guardian_by_phone.py
│   ├── get_invoices.py
│   ├── get_unread_announcements.py
│   ├── get_requests_by_guardian.py
│   ├── get_request_by_protocol.py
│   └── create_evaluation.py
└── tests/
    ├── test_router.py
    └── test_tools.py
```

## O que NÃO fazer

- Criar banco de dados próprio
- Usar token de usuário humano
- Inventar dados de boleto, prazo ou informação da escola
- Negociar dívida — sempre escalar
- Logar tokens ou dados pessoais completos
- Commitar `.env` com valores reais
