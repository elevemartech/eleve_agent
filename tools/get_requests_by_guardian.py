"""Tool: Últimas solicitações do responsável."""
from langchain_core.tools import tool
from core.api_client import DjangoAPIClient


STATUS_PT = {
    "pending":             "Pendente",
    "in_review":           "Em análise",
    "awaiting_approval":   "Aguardando aprovação",
    "approved":            "Aprovado",
    "in_progress":         "Em andamento",
    "completed":           "Concluído ✅",
    "rejected":            "Não aprovado",
    "cancelled":           "Cancelado",
}


@tool
async def get_requests_by_guardian(
    guardian_id: str,
    sa_token: str,
    **kwargs,
) -> str:
    """Retorna as últimas 5 solicitações do responsável."""
    client = DjangoAPIClient(token=sa_token)
    try:
        result = await client.get(
            "/api/v1/requests/",
            params={"siga_user_id": guardian_id, "ordering": "-created_at", "page_size": 5},
        )
        items = result.get("results", result) if isinstance(result, dict) else result

        if not items:
            return "Nenhuma solicitação encontrada para este responsável."

        lines = []
        for item in items:
            status_label = STATUS_PT.get(item.get("status", ""), item.get("status", ""))
            lines.append(
                f"• Protocolo: {item.get('protocol', '?')} | "
                f"Tipo: {item.get('request_type', '?')} | "
                f"Status: {status_label} | "
                f"Aluno: {item.get('siga_user_name', '?')}"
            )
        return "Solicitações encontradas:\n" + "\n".join(lines)

    except Exception as e:
        return f"Erro ao consultar solicitações: {e}"
