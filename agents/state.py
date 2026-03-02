"""
AgentState — estado completo do agente durante uma requisição.

Campos prefixados com _ são internos e não são persistidos no metadata.
"""
from __future__ import annotations
from typing import TypedDict


class AgentState(TypedDict, total=False):

    # ── Mensagem atual ────────────────────────────────────────────────
    input: str            # Texto normalizado (áudio/imagem já convertidos)
    phone: str
    contact_name: str

    # ── Escola (resolvido pelo school_resolver) ───────────────────────
    school_id: str
    school_name: str
    sa_token: str         # Token do ServiceAccount da escola

    # ── Sessão (attendances API) ──────────────────────────────────────
    session_id: str
    instance_token: str   # Token UazAPI ou phone_number_id Meta
    history: list[dict]   # Últimas 10 msgs [{role, content}]

    # ── Contexto do responsável (carregado pelo Identifier) ───────────
    guardian_context: dict | None
    # guardian_context = {
    #   "found": bool,
    #   "guardian_id": str,
    #   "guardian_name": str,
    #   "students": [{"id", "name", "grade", "enrollment"}]
    # }

    # ── Controle de fluxo (persiste no metadata da sessão) ────────────
    current_agent: str    # Agente ativo: greeting | faq | financial | ...
    current_step: int     # Passo do fluxo multi-etapas
    keep_flow: bool       # True = continua no agente atual
    collected_data: dict  # Dados coletados no fluxo corrente

    # ── Saída ─────────────────────────────────────────────────────────
    response: str         # Resposta final para o usuário


def metadata_from_state(state: AgentState) -> dict:
    """Extrai apenas os campos que devem ser persistidos no metadata da sessão."""
    return {
        "current_agent":    state.get("current_agent", ""),
        "current_step":     state.get("current_step", 0),
        "collected_data":   state.get("collected_data", {}),
        "guardian_context": state.get("guardian_context", None),
    }


def state_from_metadata(meta: dict) -> dict:
    """Reconstrói campos do estado a partir do metadata salvo."""
    return {
        "current_agent":    meta.get("current_agent", ""),
        "current_step":     meta.get("current_step", 0),
        "collected_data":   meta.get("collected_data", {}),
        "guardian_context": meta.get("guardian_context", None),
    }
