"""
FAQ — responde dúvidas com base nas FAQs cadastradas.

Se não encontrar resposta, cria ticket para a equipe.
"""
from __future__ import annotations

import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.state import AgentState
from core.settings import settings

logger = structlog.get_logger()

FAQ_PROMPT = """Você é o assistente de informações da {school_name}.

REGRAS:
- Responda APENAS com base nas FAQs encontradas pela tool search_faq.
- Se a FAQ não tiver a resposta, seja honesto mas gentil. Crie um ticket.
- Nunca invente informações sobre a escola.
- Se parecer interesse em matrícula, convide para o fluxo de matrícula.

FAQs encontradas:
{faq_results}

Histórico: {history}"""


async def faq_node(state: AgentState) -> AgentState:
    from tools.search_faq import search_faq
    from tools.create_ticket import create_ticket

    # Busca no FAQ
    faq_results = ""
    try:
        faq_results = await search_faq.ainvoke({
            "query": state["input"],
            "sa_token": state["sa_token"],
        })
    except Exception as e:
        logger.warning("faq_search_error", error=str(e))
        faq_results = "(erro ao buscar FAQ)"

    # Se FAQ vazio, cria ticket
    ticket_criado = False
    if not faq_results or "não encontrado" in faq_results.lower():
        try:
            await create_ticket.ainvoke({
                "subject": f"Dúvida via WhatsApp: {state['input'][:100]}",
                "description": state["input"],
                "phone": state["phone"],
                "contact_name": state.get("contact_name", ""),
                "sa_token": state["sa_token"],
            })
            ticket_criado = True
        except Exception as e:
            logger.warning("faq_ticket_error", error=str(e))

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in state.get("history", [])[-4:]
    )

    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.3,
        api_key=settings.openai_api_key,
    )

    prompt = FAQ_PROMPT.format(
        school_name=state["school_name"],
        faq_results=faq_results or "Nenhuma FAQ encontrada para esta dúvida.",
        history=history_text or "(sem histórico)",
    )

    if ticket_criado:
        prompt += "\n\nInforme que a dúvida foi encaminhada para a equipe e que entrarão em contato em breve."

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
