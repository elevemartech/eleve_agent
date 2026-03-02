"""
Enrollment — captação de matrículas.

Fluxo multi-passo. Cria EnrollmentRequest na API com protocolo.
Valida série por data de nascimento (corte 31/03).
"""
from __future__ import annotations

import json
import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.state import AgentState
from core.settings import settings

logger = structlog.get_logger()

ENROLLMENT_PROMPT = """Você é o consultor de matrículas da {school_name}.

Tom: entusiasmado, acolhedor, inspirador. Uma pergunta por vez. Máximo 2 parágrafos.

ESTADO ATUAL:
- Passo: {step}
- Dados coletados: {collected}

FLUXO (uma pergunta por vez, nesta ordem):
1. Quantos alunos deseja matricular?
2. Nome do responsável
3. Nome e data de nascimento do aluno
4. Valide a idade com o corte de 31/03 do ano letivo. Sugira série correta se necessário.
5. Segmento (Infantil / Fundamental I / Fundamental II / Ensino Médio)
6. Série dentro do segmento
7. Turno (manhã / tarde / integral)
8. Tipo (nova matrícula / rematrícula / transferência)
9. E-mail do responsável
10. Registro na API (chame create_enrollment)
11. Convide para visita: "Que tal conhecer a escola? Posso te enviar o link para agendar."
12. Se aceitar: envie o link de visita.
13. "Posso ajudar com mais alguma coisa?"

RESULTADO DO REGISTRO:
{enrollment_result}

Histórico: {history}

REGRAS:
- Nunca pule etapas. Nunca invente dados.
- Corte de série: criança deve ter a idade mínima até 31/03 do ano letivo.
- Se desistir a qualquer momento, finalize graciosamente."""


async def enrollment_node(state: AgentState) -> AgentState:
    from tools.create_enrollment import create_enrollment

    step = state.get("current_step", 0)
    collected = state.get("collected_data", {})
    enrollment_result = ""

    # Tenta criar enrollment quando tiver dados suficientes (passo 10)
    if step >= 9 and collected.get("candidate_name") and collected.get("responsible_name"):
        try:
            result = await create_enrollment.ainvoke({
                "candidate_name": collected.get("candidate_name", ""),
                "candidate_dob": collected.get("candidate_dob", ""),
                "responsible_name": collected.get("responsible_name", ""),
                "responsible_email": collected.get("responsible_email", ""),
                "desired_grade": collected.get("desired_grade", ""),
                "desired_shift": collected.get("desired_shift", ""),
                "request_type": collected.get("request_type", "nova"),
                "phone": state["phone"],
                "sa_token": state["sa_token"],
                "session_id": state.get("session_id", ""),
            })
            enrollment_result = result
        except Exception as e:
            logger.error("enrollment_create_error", error=str(e))
            enrollment_result = f"Erro ao registrar: {e}"

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in state.get("history", [])[-6:]
    )

    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.4,
        api_key=settings.openai_api_key,
    )

    prompt = ENROLLMENT_PROMPT.format(
        school_name=state["school_name"],
        step=step,
        collected=json.dumps(collected, ensure_ascii=False),
        enrollment_result=enrollment_result or "(aguardando dados completos)",
        history=history_text or "(sem histórico)",
    )

    result = await llm.ainvoke([
        SystemMessage(content=prompt),
        HumanMessage(content=state["input"]),
    ])

    response = result.content.strip()
    next_step = min(step + 1, 13)
    finished = step >= 13

    return {
        **state,
        "response": response,
        "current_step": 0 if finished else next_step,
        "current_agent": "" if finished else "enrollment",
        "collected_data": collected,
    }
