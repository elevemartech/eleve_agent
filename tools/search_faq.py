"""Tool: Busca perguntas frequentes cadastradas pela escola."""
from langchain_core.tools import tool
from core.api_client import DjangoAPIClient


@tool
async def search_faq(query: str, sa_token: str, **kwargs) -> str:
    """Busca respostas para dúvidas nas FAQs cadastradas pela escola."""
    client = DjangoAPIClient(token=sa_token)
    try:
        result = await client.get("/api/v1/faqs/", params={"search": query, "is_active": "true"})
        items = result.get("results", result) if isinstance(result, dict) else result
        if not items:
            return "Nenhuma FAQ encontrada para esta dúvida."
        lines = [f"P: {item['question']}\nR: {item['answer']}" for item in items[:3]]
        return "\n\n".join(lines)
    except Exception as e:
        return f"Erro ao buscar FAQ: {e}"
