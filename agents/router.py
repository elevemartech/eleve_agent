"""
Router — classifica a intenção do usuário e decide qual agente executar.

Saída JSON: {"agent": "financial", "keep_flow": false, "confidence": 0.94}

keep_flow=true  → usuário está respondendo pergunta do agente atual (continua)
keep_flow=false → novo assunto ou sessão nova (roteia para agente correto)
"""
from __future__ import annotations

import json
import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.state import AgentState
from core.settings import settings

logger = structlog.get_logger()

ROUTER_PROMPT = """Você é um classificador de intenções para um assistente escolar via WhatsApp.

AGENTES DISPONÍVEIS:
- greeting      → Saudação, início de conversa sem contexto específico
- financial     → Boleto, mensalidade, pagamento, inadimplência, financeiro
- secretary     → Documentos: declaração, histórico, lista de materiais, transferência
- enrollment    → Matrícula, vaga, visita à escola, interesse em matrícula
- faq           → Dúvidas gerais, horário, calendário, uniforme, metodologia
- protocol      → Consultar status de uma solicitação ou protocolo existente
- announcement  → Comunicados, avisos, notícias da escola
- human         → Pedido explícito de atendimento humano, insatisfação forte
- closing       → Agradecimento, despedida, fim do atendimento

REGRAS DE KEEP_FLOW:
- keep_flow=true quando o usuário claramente responde uma pergunta do agente atual
  (respostas curtas: nome, número, "sim", "não", data, série)
- keep_flow=false quando há mudança de assunto ou é uma nova sessão

Contexto:
- Agente atual: {current_agent}
- Passo atual: {current_step}
- Última mensagem do agente: {last_agent_message}

Responda APENAS com JSON válido, sem explicações:
{{"agent": "nome_do_agente", "keep_flow": true|false, "confidence": 0.0}}"""


async def router_node(state: AgentState) -> AgentState:
    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0,
        api_key=settings.openai_api_key,
    )

    history = state.get("history", [])
    last_agent_msg = next(
        (m["content"] for m in reversed(history) if m["role"] == "agent"), ""
    )

    prompt = ROUTER_PROMPT.format(
        current_agent=state.get("current_agent", ""),
        current_step=state.get("current_step", 0),
        last_agent_message=last_agent_msg[:200] if last_agent_msg else "(sem histórico)",
    )

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=state["input"]),
    ]

    try:
        result = await llm.ainvoke(messages)
        raw = result.content.strip()
        parsed = json.loads(raw)
        agent = parsed.get("agent", "faq")
        keep_flow = parsed.get("keep_flow", False)
        confidence = parsed.get("confidence", 0.8)

        logger.info(
            "router_decision",
            agent=agent,
            keep_flow=keep_flow,
            confidence=confidence,
            phone=state["phone"][-4:],
        )

        # Se keep_flow, mantém o agente atual
        if keep_flow and state.get("current_agent"):
            agent = state["current_agent"]

        return {**state, "current_agent": agent, "keep_flow": keep_flow}

    except (json.JSONDecodeError, Exception) as e:
        logger.error("router_error", error=str(e))
        return {**state, "current_agent": "faq", "keep_flow": False}


def route_to_agent(state: AgentState) -> str:
    """Função de roteamento condicional do LangGraph."""
    return state.get("current_agent", "faq")
