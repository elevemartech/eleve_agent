"""Tool: Busca comunicados não lidos — urgentes primeiro."""
from langchain_core.tools import tool
from core.api_client import DjangoAPIClient


@tool
async def get_unread_announcements(sa_token: str, phone: str = "", **kwargs) -> str:
    """Retorna comunicados recentes da escola, urgentes primeiro."""
    client = DjangoAPIClient(token=sa_token)
    try:
        result = await client.get(
            "/api/v1/management/announcements/",
            params={"published": "true", "ordering": "-pinned,-published_at"},
        )
        items = result.get("results", result) if isinstance(result, dict) else result

        if not items:
            return ""

        urgent = [i for i in items if i.get("type") == "urgente"]
        others = [i for i in items if i.get("type") != "urgente"][:2]

        lines = []
        for item in urgent + others:
            tipo = "🔴 URGENTE" if item.get("type") == "urgente" else "📢 Comunicado"
            lines.append(f"{tipo}: {item['title']}\n{item.get('body', '')[:200]}")

        return "\n\n".join(lines) if lines else ""

    except Exception:
        return ""
