"""Tool: Cria ticket para a equipe quando o FAQ não tem resposta."""
from langchain_core.tools import tool
from core.api_client import DjangoAPIClient


@tool
async def create_ticket(
    subject: str,
    description: str,
    phone: str,
    contact_name: str = "",
    sa_token: str = "",
    **kwargs,
) -> str:
    """Cria um ticket para a equipe escolar responder ao responsável."""
    client = DjangoAPIClient(token=sa_token)
    try:
        result = await client.post("/api/v1/tickets/", json={
            "subject": subject,
            "description": description,
            "requester_phone": phone,
            "requester_name": contact_name,
            "channel": "whatsapp",
            "category": "informacao",
        })
        protocol = result.get("protocol", result.get("id", ""))
        return f"Ticket criado — protocolo {protocol}. A equipe retornará em breve."
    except Exception as e:
        return f"Não foi possível criar o ticket: {e}"
