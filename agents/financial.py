"""
Financial — atendimento financeiro.

Consulta boletos em tempo real via SIGA.
Nunca negocia dívida — escala para humano.
"""
from __future__ import annotations

import json
import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.state import AgentState
from core.settings import settings

logger = structlog.get_logger()

FINANCIAL_PROMPT = """Você é o assistente financeiro da {school_name}.

REGRAS ABSOLUTAS:
- NUNCA negocie dívidas, prometa desconto ou parcelamento. Se pedir isso, diga que irá
  transferir para um especialista.
- NUNCA invente valores ou datas. Use APENAS os dados retornados pelas tools.
- Se não encontrar o responsável no sistema, peça o nome completo do aluno.

Contexto do responsável:
{guardian_context}

Histórico: {history}

Dados disponíveis (resultado das tools chamadas):
{tool_results}"""


async def financial_node(state: AgentState) -> AgentState:
    from tools.get_guardian_by_phone import get_guardian_by_phone
    from tools.get_invoices import get_invoices

    tool_results = []
    guardian_context = state.get("guardian_context")

    # 1. Identifica responsável se ainda não foi feito
    if not guardian_context:
        try:
            result = await get_guardian_by_phone.ainvoke({
                "phone": state["phone"],
                "sa_token": state["sa_token"],
            })
            tool_results.append(f"Identificação: {result}")

            if isinstance(result, str) and "{" in result:
                guardian_context = json.loads(result)
        except Exception as e:
            logger.warning("financial_identify_error", error=str(e))
            tool_results.append("Identificação: responsável não encontrado no sistema")

    # 2. Busca boletos se responsável foi identificado
    if guardian_context and guardian_context.get("found"):
        # CORREÇÃO: usa siga_guardian_id (inteiro do SIGA), não guardian_id (UUID).
        # O endpoint GET /contacts/guardians/{id}/invoices/ faz int(pk) internamente.
        siga_guardian_id = guardian_context.get("siga_guardian_id")

        if siga_guardian_id:
            try:
                invoices_result = await get_invoices.ainvoke({
                    "siga_guardian_id": siga_guardian_id,
                    "sa_token": state["sa_token"],
                })
                tool_results.append(f"Boletos: {invoices_result}")
            except Exception as e:
                logger.warning("financial_invoices_error", error=str(e))
                tool_results.append("Boletos: erro ao consultar — tente novamente em instantes")
        else:
            tool_results.append("Boletos: siga_guardian_id não disponível para este responsável.")

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in state.get("history", [])[-6:]
    )

    guardian_ctx_text = (
        str(guardian_context) if guardian_context else "Responsável não identificado ainda"
    )

    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.3,
        api_key=settings.openai_api_key,
    )

    prompt = FINANCIAL_PROMPT.format(
        school_name=state["school_name"],
        guardian_context=guardian_ctx_text,
        history=history_text or "(sem histórico)",
        tool_results="\n".join(tool_results) or "(sem dados carregados)",
    )

    result = await llm.ainvoke([
        SystemMessage(content=prompt),
        HumanMessage(content=state["input"]),
    ])

    response = result.content.strip()

    # Detecta necessidade de escalação
    escalation_keywords = ["negoci", "desconto", "parcel", "dívida", "inadimpl", "acordo"]
    needs_escalation = any(kw in state["input"].lower() for kw in escalation_keywords)

    return {
        **state,
        "response": response,
        "guardian_context": guardian_context,
        "current_agent": "human" if needs_escalation else "financial",
        "current_step": 0,
    }