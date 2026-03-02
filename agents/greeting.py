"""
Greeting — boas-vindas e menu inicial.

Verifica comunicados urgentes não lidos e informa o usuário.
"""
from __future__ import annotations

import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.state import AgentState
from core.settings import settings

logger = structlog.get_logger()

GREETING_PROMPT = """Você é o assistente virtual da {school_name} no WhatsApp.

Tom: amigável, profissional e acolhedor. Português claro. Sem exageros.
Máximo 3 parágrafos curtos por resposta.

{comunicados_urgentes}

Apresente-se brevemente (se for primeira mensagem) e ofereça as opções:
1. 💰 Financeiro — boletos e pagamentos
2. 📋 Secretaria — documentos e solicitações
3. 🎓 Matrícula — informações e interesse
4. ❓ Dúvidas — horários, calendário, uniforme

Se o usuário já indicou o que quer, não apresente o menu — responda diretamente.

Histórico recente: {history}"""


async def greeting_node(state: AgentState) -> AgentState:
    from tools.get_unread_announcements import get_unread_announcements

    # Verifica comunicados urgentes
    comunicados_bloco = ""
    try:
        comunicados_raw = await get_unread_announcements.ainvoke({
            "sa_token": state["sa_token"],
            "phone": state["phone"],
        })
        if comunicados_raw and "urgente" in comunicados_raw.lower():
            comunicados_bloco = f"\nIMPORTANTE — Informe sobre este comunicado não lido:\n{comunicados_raw}\n"
    except Exception:
        pass

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in state.get("history", [])[-4:]
    )

    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.4,
        api_key=settings.openai_api_key,
    )

    prompt = GREETING_PROMPT.format(
        school_name=state["school_name"],
        comunicados_urgentes=comunicados_bloco,
        history=history_text or "(sem histórico)",
    )

    result = await llm.ainvoke([
        SystemMessage(content=prompt),
        HumanMessage(content=state["input"]),
    ])

    return {
        **state,
        "response": result.content.strip(),
        "current_agent": "",
        "current_step": 0,
    }
