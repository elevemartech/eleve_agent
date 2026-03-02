"""Tool: Cria solicitação na API com protocolo e card automático no board."""
from langchain_core.tools import tool
from core.api_client import DjangoAPIClient


@tool
async def create_request(
    request_type: str,
    description: str,
    student_name: str = "",
    phone: str = "",
    contact_name: str = "",
    sa_token: str = "",
    session_id: str = "",
    **kwargs,
) -> str:
    """
    Cria uma solicitação de documento ou serviço.
    Tipos: boleto_2via | declaracao | historico | transferencia | rematricula | cancelamento | outros
    """
    client = DjangoAPIClient(token=sa_token)
    try:
        payload = {
            "request_type": request_type,
            "description": description or f"Solicitação de {request_type} para {student_name}",
            "siga_user_name": student_name,
            "requester_phone": phone,
            "requester_name": contact_name,
            "channel": "whatsapp",
        }
        if session_id:
            payload["session_id"] = session_id

        result = await client.post("/api/v1/requests/", json=payload)
        protocol = result.get("protocol", result.get("id", ""))
        return (
            f"Solicitação criada com sucesso!\n"
            f"Protocolo: {protocol}\n"
            f"Tipo: {request_type}\n"
            f"Acompanhe o status pelo mesmo número."
        )
    except Exception as e:
        return f"Não foi possível criar a solicitação: {e}"
