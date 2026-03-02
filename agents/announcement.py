"""
Announcement — leitura de comunicados específicos.
"""
from __future__ import annotations

import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.state import AgentState
from core.settings import settings

logger = structlog.get_logger()

ANNOUNCEMENT_PROMPT = """Você é o assistente de comunicados da {school_name}.

Comunicados disponíveis:
{announcement_data}

Apresente as informações de forma clara e amigável.
Se for um comunicado urgente, destaque isso.
Após apresentar, pergunte se o responsável deseja mais detalhes ou tem alguma dúvida.

Histórico: {history}"""


async def announcement_node(state: AgentState) -> AgentState:
    from tools.get_unread_announcements import get_unread_announcements

    announcement_data = ""
    try:
        announcement_data = await get_unread_announcements.ainvoke({
            "sa_token": state["sa_token"],
            "phone": state["phone"],
        })
    except Exception as e:
        logger.warning("announcement_error", error=str(e))
        announcement_data = "Não foi possível carregar os comunicados no momento."

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in state.get("history", [])[-4:]
    )

    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.3,
        api_key=settings.openai_api_key,
    )

    result = await llm.ainvoke([
        SystemMessage(content=ANNOUNCEMENT_PROMPT.format(
            school_name=state["school_name"],
            announcement_data=announcement_data or "Sem comunicados recentes.",
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
