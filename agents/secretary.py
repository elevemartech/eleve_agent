"""
Secretary — solicitações de documentos com protocolo.

Fluxo multi-passo. Estado persiste via current_step e collected_data.
Tipos: boleto_2via, declaracao, historico, transferencia, rematricula, cancelamento, outros.
"""
from __future__ import annotations

import json
import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.state import AgentState
from core.settings import settings

logger = structlog.get_logger()

# Tipos que NÃO precisam de aprovação de manager
AUTO_TYPES = {"boleto_2via", "declaracao", "historico"}

SECRETARY_PROMPT = """Você é a secretaria virtual da {school_name}.

Tom: profissional, acolhedor, objetivo. UMA pergunta por vez.

ESTADO ATUAL:
- Passo: {step}
- Dados coletados: {collected}

FLUXO (siga exatamente, uma pergunta por vez):
Passo 0 → Pergunte o que o responsável precisa. Classifique em:
  boleto_2via | declaracao | historico | transferencia | rematricula | cancelamento | outros

Passo 1 → Colete dados específicos por tipo:
  - boleto_2via: nome do aluno e mês de referência
  - declaracao: nome do aluno e finalidade (matrícula, frequência, conclusão)
  - historico: nome do aluno e ano letivo
  - transferencia: nome do aluno e escola de destino
  - rematricula: nome do aluno e série desejada
  - cancelamento: nome do aluno e motivo
  - outros: descrição completa da necessidade

Passo 2 → Confirme os dados e processe (chame create_request)

Passo 3 → Informe o protocolo gerado e prazo estimado. Encerre.

RESULTADO DA CRIAÇÃO:
{request_result}

Histórico: {history}"""


async def secretary_node(state: AgentState) -> AgentState:
    from tools.create_request import create_request

    step = state.get("current_step", 0)
    collected = state.get("collected_data", {})
    request_result = ""

    # Passo 2: criar solicitação se tiver tipo e dados
    if step == 2 and collected.get("request_type") and collected.get("student_name"):
        try:
            result = await create_request.ainvoke({
                "request_type": collected["request_type"],
                "description": collected.get("description", ""),
                "student_name": collected.get("student_name", ""),
                "phone": state["phone"],
                "contact_name": state.get("contact_name", ""),
                "sa_token": state["sa_token"],
                "session_id": state.get("session_id", ""),
            })
            request_result = result
            step = 3
        except Exception as e:
            logger.error("secretary_create_error", error=str(e))
            request_result = "Erro ao criar solicitação — tente novamente."

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in state.get("history", [])[-6:]
    )

    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.3,
        api_key=settings.openai_api_key,
    )

    prompt = SECRETARY_PROMPT.format(
        school_name=state["school_name"],
        step=step,
        collected=json.dumps(collected, ensure_ascii=False),
        request_result=request_result or "(aguardando dados completos)",
        history=history_text or "(sem histórico)",
    )

    result = await llm.ainvoke([
        SystemMessage(content=prompt),
        HumanMessage(content=state["input"]),
    ])

    response = result.content.strip()

    # Avança passo se for passo de coleta
    next_step = step + 1 if step < 3 else 0
    still_active = step < 3

    return {
        **state,
        "response": response,
        "current_step": next_step if still_active else 0,
        "current_agent": "secretary" if still_active else "",
        "collected_data": collected,
    }
