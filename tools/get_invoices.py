"""Tool: Consulta boletos em aberto do responsável em tempo real via SIGA."""
from langchain_core.tools import tool
from core.api_client import DjangoAPIClient


SITUACAO_MAP = {
    "ABE": "Em aberto",
    "LIQ": "Pago",
    "CAN": "Cancelado",
    "VEN": "Vencido",
}


@tool
async def get_invoices(
    siga_guardian_id: str,
    sa_token: str,
    situacao: str = "ABE",
    **kwargs,
) -> str:
    """
    Retorna boletos do responsável. situacao: ABE (aberto) | LIQ (pago) | CAN (cancelado).
    Padrão: apenas boletos em aberto.
    Requer siga_guardian_id — ID inteiro do responsável no SIGA (não o UUID interno).
    """
    # CORREÇÃO: o parâmetro era `guardian_id` (UUID do model people.Guardian),
    # mas o endpoint GET /api/v1/contacts/guardians/{id}/invoices/ faz int(pk)
    # internamente — UUID causa ValueError 400. O campo correto é siga_guardian_id,
    # disponível no guardian_context desde a correção de get_guardian_by_phone.
    if not siga_guardian_id:
        return "Não foi possível consultar os boletos: siga_guardian_id não informado."

    client = DjangoAPIClient(token=sa_token)
    try:
        result = await client.get(
            f"/api/v1/contacts/guardians/{siga_guardian_id}/invoices/",
            params={"situacao": situacao},
        )

        filhos = result.get("filhos", [])
        resumo = result.get("resumo_geral", {})

        if not filhos or resumo.get("total_abertos", 0) == 0:
            return "Não há boletos em aberto para esta conta."

        lines = []
        for filho in filhos:
            boletos = filho.get("boletos", [])
            if not boletos:
                continue
            for b in boletos:
                sit = SITUACAO_MAP.get(b.get("situacao", ""), b.get("situacao", ""))
                lines.append(
                    f"• Aluno: {filho['nome']} | "
                    f"Valor: R$ {b.get('valor', '?')} | "
                    f"Vencimento: {b.get('vencimento', '?')} | "
                    f"Situação: {sit}"
                )

        if not lines:
            return "Não há boletos em aberto."

        total_pendente = resumo.get("valor_total_pendente", 0)
        header = f"Boletos em aberto (total pendente: R$ {total_pendente}):\n"
        return header + "\n".join(lines)

    except Exception as e:
        return f"Não foi possível consultar os boletos: {e}"