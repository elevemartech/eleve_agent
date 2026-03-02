"""
Eleve Agent — FastAPI + LangGraph

Webhook principal que orquestra:
  1. Identificação da escola (school_resolver)
  2. Agrupamento de mensagens (message_batcher)
  3. Processamento de mídia (media_handler)
  4. Sessão de atendimento (session_manager)
  5. Execução do grafo de agentes (LangGraph)
  6. Envio da resposta (WhatsApp provider)
"""
from __future__ import annotations

import asyncio
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, BackgroundTasks, HTTPException

from core.settings import settings
from core.school_resolver import resolve_school
from core.session_manager import SessionManager
from core.message_batcher import add_message, wait_and_collect
from core.media_handler import process as process_media
from core.whatsapp.factory import get_provider
from agents.state import AgentState, metadata_from_state, state_from_metadata
from agents.graph import agent_graph

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(__import__("logging"), settings.log_level)
        )
    )
    logger.info("eleve_agent_started", environment=settings.environment)
    yield
    logger.info("eleve_agent_stopped")


app = FastAPI(
    title="Eleve Agent",
    version="1.0.0",
    description="Agente de IA para comunicação escola-família via WhatsApp",
    lifespan=lifespan,
)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.environment}


# ── Verificação Meta (GET /webhook) ──────────────────────────────────────────

@app.get("/webhook")
async def meta_verify(request: Request):
    params = dict(request.query_params)
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == settings.meta_verify_token
    ):
        return Response(content=params["hub.challenge"], media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verify token inválido")


# ── Webhook principal (POST /webhook) ────────────────────────────────────────

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    background_tasks.add_task(handle_message, payload)
    return {"status": "received"}


async def handle_message(payload: dict) -> None:
    """Processa mensagem recebida do WhatsApp em background."""

    # 1. Identifica escola pelo token da instância
    # Tenta UazAPI primeiro, depois Meta
    instance_token = (
        payload.get("instance")
        or payload.get("instanceId")
        or _extract_meta_phone_number_id(payload)
    )

    if not instance_token:
        logger.warning("webhook_no_instance_token")
        return

    school = await resolve_school(instance_token)
    if not school:
        logger.warning("webhook_school_not_found", token=instance_token[-6:])
        return

    provider = get_provider(school)

    # 2. Extrai dados da mensagem
    phone = provider.extract_phone(payload)
    if not phone:
        return

    msg_type = provider.extract_message_type(payload)
    contact_name = provider.extract_contact_name(payload)

    # 3. Processa mídia se necessário
    if msg_type in ("audio", "ptt", "image", "document"):
        media_url = provider.extract_media_url(payload)
        mime_type = provider.extract_mime_type(payload)
        if media_url:
            text = await process_media(msg_type, media_url, mime_type)
            if not text:
                return  # Mídia ignorada (sticker, etc)
        else:
            return
    elif msg_type == "text":
        text = provider.extract_text(payload)
        if not text:
            return
    else:
        return  # Tipo não suportado

    # 4. Adiciona ao batcher e aguarda debounce
    await add_message(school["school_id"], phone, text)
    batched_text = await wait_and_collect(school["school_id"], phone)

    if not batched_text:
        # Outra mensagem chegou — esse worker foi suplantado
        return

    # 5. Busca/cria sessão
    sm = SessionManager(school["sa_token"])
    session, _ = await sm.find_or_create(
        phone=phone,
        channel="whatsapp",
        contact_name=contact_name,
        message=batched_text,
    )
    session_id = str(session["id"])

    # 6. Carrega histórico e metadata
    history = await sm.get_history(session_id, limit=10)
    metadata = await sm.get_metadata(session_id)

    # 7. Monta estado inicial
    initial_state: AgentState = {
        "input": batched_text,
        "phone": phone,
        "contact_name": contact_name,
        "school_id": school["school_id"],
        "school_name": school["school_name"],
        "sa_token": school["sa_token"],
        "session_id": session_id,
        "instance_token": instance_token,
        "history": history,
        "response": "",
        **state_from_metadata(metadata),
    }

    logger.info(
        "processing_message",
        school=school["school_name"],
        phone=phone[-4:],
        session_id=session_id,
        agent=initial_state.get("current_agent", "—"),
    )

    # 8. Executa grafo LangGraph
    try:
        result = await agent_graph.ainvoke(initial_state)
    except Exception as e:
        logger.error("graph_error", error=str(e), phone=phone[-4:])
        result = {**initial_state, "response": "Desculpe, ocorreu um erro. Tente novamente em instantes."}

    response_text = result.get("response", "")
    if not response_text:
        return

    # 9. Salva mensagem do agente + metadata atualizado
    await asyncio.gather(
        sm.save_message(session_id, role="agent", content=response_text),
        sm.save_metadata(session_id, metadata_from_state(result)),
        return_exceptions=True,
    )

    # 10. Envia resposta ao WhatsApp
    try:
        if isinstance(provider, __import__("core.whatsapp.uazapi", fromlist=["UazAPIProvider"]).UazAPIProvider):
            await provider.send_text(phone, response_text, instance_token=instance_token)
        else:
            await provider.send_text(phone, response_text)
    except Exception as e:
        logger.error("send_error", error=str(e), phone=phone[-4:])


def _extract_meta_phone_number_id(payload: dict) -> str | None:
    try:
        return payload["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
    except (KeyError, IndexError):
        return None
