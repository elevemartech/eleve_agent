"""Tool: Busca solicitação por número de protocolo."""
from langchain_core.tools import tool
from core.api_client import DjangoAPIClient


@tool
async def get_request_by_protocol(protocol: str, sa_token: str, **kwargs) -> str:
    """Busca uma solicitação pelo número de protocolo (ex: REQ-2026-0045)."""
    client = DjangoAPIClient(token=sa_token)
    try:
        result = await client.get("/api/v1/requests/", params={"search": protocol})
        items = result.get("results", result) if isinstance(result, dict) else result

        if not items:
            return f"Protocolo {protocol} não encontrado."

        item = items[0]
        return (
            f"Protocolo: {item.get('protocol')}\n"
            f"Tipo: {item.get('request_type')}\n"
            f"Aluno: {item.get('siga_user_name', 'não informado')}\n"
            f"Status: {item.get('status')}\n"
            f"Criado em: {item.get('created_at', '')[:10]}"
        )
    except Exception as e:
        return f"Erro ao buscar protocolo: {e}"
