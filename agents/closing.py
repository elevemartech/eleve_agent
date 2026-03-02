"""
Closing — encerramento com NPS real salvo na API.

Passo 0: pergunta nota de 0 a 10
Passo 1: agradece, salva avaliação, encerra sessão
"""
from __future__ import annotations

import re
import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.state import AgentState
from core.session_manager import SessionManager
from core.settings import settings

logger = structlog.get_logger()

CLOSING_PROMPT_NPS = """Você é o assistente da {school_name}.

O atendimento chegou ao fim. Solicite uma avaliação de forma leve e natural.
Peça uma nota de 0 a 10 para o atendimento de hoje.
Seja breve — máximo 2 frases."""

CLOSING_PROMPT_THANKS = """Você é o assistente da {school_name}.

O responsável deu nota {nota} para o atendimento.

Agradeça de forma genuína e proporcional à nota:
- Nota >= 9: entusiasmado e grato
- Nota 7-8: positivo e receptivo a melhorias
- Nota <= 6: empático, reconheça que pode melhorar e agradeça o feedback

Despeça-se com carinho. Máximo 3 frases."""


async def closing_node(state: AgentState) -> AgentState:
    from tools.create_evaluation import create_evaluation

    step = state.get("current_step", 0)
    sm = SessionManager(state["sa_token"])

    if step == 0:
        # Pede NPS
        llm = ChatOpenAI(model=settings.openai_model, temperature=0.4, api_key=settings.openai_api_key)
        result = await llm.ainvoke([
            SystemMessage(content=CLOSING_PROMPT_NPS.format(school_name=state["school_name"])),
            HumanMessage(content=state["input"]),
        ])
        return {
            **state,
            "response": result.content.strip(),
            "current_agent": "closing",
            "current_step": 1,
        }

    # Passo 1: processa nota e encerra
    nota = None
    match = re.search(r"\b([0-9]|10)\b", state["input"])
    if match:
        nota = int(match.group())

    # Salva avaliação na API
    if nota is not None:
        try:
            await create_evaluation.ainvoke({
                "name": state.get("contact_name", "Não identificado"),
                "phone": state["phone"],
                "rating": nota,
                "channel": "whatsapp",
                "session_id": state.get("session_id", ""),
                "sa_token": state["sa_token"],
            })
            logger.info("nps_saved", rating=nota, phone=state["phone"][-4:])
        except Exception as e:
            logger.warning("nps_save_error", error=str(e))

    # Encerra sessão
    try:
        await sm.close(
            session_id=state["session_id"],
            reason="resolved",
            summary=f"NPS: {nota}/10" if nota is not None else "Encerrado sem nota",
        )
    except Exception as e:
        logger.warning("session_close_error", error=str(e))

    # Mensagem de despedida
    llm = ChatOpenAI(model=settings.openai_model, temperature=0.5, api_key=settings.openai_api_key)
    result = await llm.ainvoke([
        SystemMessage(content=CLOSING_PROMPT_THANKS.format(
            school_name=state["school_name"],
            nota=nota if nota is not None else "não informada",
        )),
        HumanMessage(content=state["input"]),
    ])

    return {
        **state,
        "response": result.content.strip(),
        "current_agent": "",
        "current_step": 0,
        "collected_data": {},
    }
