"""
Protocol — consulta de protocolo de solicitação existente.
"""
from __future__ import annotations

import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.state import AgentState
from core.settings import settings

logger = structlog.get_logger()

PROTOCOL_PROMPT = """Você é o assistente de acompanhamento da {school_name}.

Dados da consulta:
{protocol_data}

Com base nos dados acima, informe o status da solicitação de forma clara e humana.

Status → O que dizer:
- pending / in_review      → "Em análise — prazo estimado de X dias úteis"
- in_progress              → "Em elaboração — em breve ficará pronto"
- completed                → "Pronto! Como deseja receber o documento?"
- rejected                 → "Não foi possível processar — {motivo}. Posso ajudar a abrir uma nova solicitação?"
- cancelled                → "Solicitação cancelada. Posso ajudar a abrir uma nova?"

Histórico: {history}"""


async def protocol_node(state: AgentState) -> AgentState:
    from tools.get_request_by_protocol import get_request_by_protocol
    from tools.get_requests_by_guardian import get_requests_by_guardian

    protocol_data = ""

    # Tenta extrair número de protocolo da mensagem
    import re
    match = re.search(r"[A-Z]{2,4}-\d{4}-\d{4}", state["input"].upper())

    if match:
        try:
            protocol_data = await get_request_by_protocol.ainvoke({
                "protocol": match.group(),
                "sa_token": state["sa_token"],
            })
        except Exception as e:
            logger.warning("protocol_search_error", error=str(e))

    # Se não encontrou por protocolo e tem guardian_context, busca por responsável
    if not protocol_data and state.get("guardian_context", {}).get("found"):
        guardian_id = state["guardian_context"].get("guardian_id", "")
        if guardian_id:
            try:
                protocol_data = await get_requests_by_guardian.ainvoke({
                    "guardian_id": guardian_id,
                    "sa_token": state["sa_token"],
                })
            except Exception as e:
                logger.warning("protocol_guardian_error", error=str(e))

    if not protocol_data:
        protocol_data = "Não foi possível localizar solicitações com as informações fornecidas."

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in state.get("history", [])[-4:]
    )

    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.2,
        api_key=settings.openai_api_key,
    )

    result = await llm.ainvoke([
        SystemMessage(content=PROTOCOL_PROMPT.format(
            school_name=state["school_name"],
            protocol_data=protocol_data,
            history=history_text or "(sem histórico)",
        )),
        HumanMessage(content=state["input"]),
    ])

    return {
        **state,
        "response": result.content.strip(),
        "current_agent": "",
        "current_step": 0,
    }
