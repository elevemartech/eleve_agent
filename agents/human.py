"""
Human — escalação para operador humano.

Transfere a sessão com todo o histórico visível no painel da escola.
"""
from __future__ import annotations

import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.state import AgentState
from core.session_manager import SessionManager
from core.settings import settings

logger = structlog.get_logger()

HUMAN_PROMPT = """Você é o assistente da {school_name}.

O atendimento será transferido para um especialista humano.

Comunique a transferência de forma:
- Tranquilizadora: o responsável será atendido em breve
- Clara: informe que o histórico da conversa estará disponível para o atendente
- Sem prazo específico: não prometa horário exato
- Empática: reconheça a situação sem confirmar nada que não saiba

Motivo da escalação: {reason}
Histórico: {history}"""


async def human_node(state: AgentState) -> AgentState:
    sm = SessionManager(state["sa_token"])

    # Determina motivo da escalação
    reason = state.get("collected_data", {}).get("escalation_reason", "Solicitado pelo usuário")

    # Efetua a escalação na API
    try:
        await sm.escalate(
            session_id=state["session_id"],
            reason=reason,
        )
        logger.info(
            "session_escalated",
            session_id=state["session_id"],
            reason=reason,
            phone=state["phone"][-4:],
        )
    except Exception as e:
        logger.error("escalation_error", error=str(e))

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in state.get("history", [])[-4:]
    )

    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.4,
        api_key=settings.openai_api_key,
    )

    result = await llm.ainvoke([
        SystemMessage(content=HUMAN_PROMPT.format(
            school_name=state["school_name"],
            reason=reason,
            history=history_text or "(sem histórico)",
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
