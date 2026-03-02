"""Tool: Salva avaliação NPS na API para alimentar o dashboard da escola."""
from langchain_core.tools import tool
from core.api_client import DjangoAPIClient


@tool
async def create_evaluation(
    name: str,
    phone: str,
    rating: int,
    channel: str = "whatsapp",
    session_id: str = "",
    sa_token: str = "",
    **kwargs,
) -> str:
    """
    Salva avaliação NPS (0-10) na API da escola.
    channel: whatsapp | telefone | presencial | email | app
    """
    client = DjangoAPIClient(token=sa_token)
    try:
        payload = {
            "name": name,
            "phone": phone,
            "rating": max(0, min(10, int(rating))),
            "channel": channel,
            "attendance_type": "whatsapp",
        }
        if session_id:
            payload["session_id"] = session_id

        await client.post("/api/v1/evaluations/", json=payload)
        return f"Avaliação {rating}/10 salva com sucesso."
    except Exception as e:
        return f"Não foi possível salvar a avaliação: {e}"
