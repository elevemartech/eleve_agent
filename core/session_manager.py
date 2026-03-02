"""
Integração com /api/v1/attendances/sessions/ da Eleve API.

Responsável por criar/buscar sessões, salvar mensagens,
registrar ações e persistir metadata entre turnos.
"""
from __future__ import annotations

import structlog
from core.api_client import DjangoAPIClient

logger = structlog.get_logger()


class SessionManager:
    def __init__(self, sa_token: str):
        self.client = DjangoAPIClient(token=sa_token)

    async def find_or_create(
        self,
        phone: str,
        channel: str = "whatsapp",
        contact_name: str = "",
        message: str = "",
    ) -> tuple[dict, bool]:
        """
        POST /attendances/sessions/webhook/
        Retorna (sessão, criada).
        """
        data = await self.client.post(
            "/api/v1/attendances/sessions/webhook/",
            json={
                "phone": phone,
                "channel": channel,
                "contact_name": contact_name,
                "message": message,
                "message_type": "text",
            },
        )
        return data["session"], data["created"]

    async def get_history(self, session_id: str, limit: int = 10) -> list[dict]:
        """Últimas N mensagens da sessão."""
        session = await self.client.get(f"/api/v1/attendances/sessions/{session_id}/")
        messages = session.get("messages", [])[-limit:]
        return [{"role": m["role"], "content": m["content"]} for m in messages]

    async def get_metadata(self, session_id: str) -> dict:
        """Retorna o metadata da sessão (estado persistido entre turnos)."""
        session = await self.client.get(f"/api/v1/attendances/sessions/{session_id}/")
        return session.get("metadata", {})

    async def save_metadata(self, session_id: str, metadata: dict) -> None:
        """Persiste estado do agente no metadata da sessão."""
        await self.client.patch(
            f"/api/v1/attendances/sessions/{session_id}/",
            json={"metadata": metadata},
        )

    async def save_message(self, session_id: str, role: str, content: str) -> None:
        """POST /sessions/{id}/message/"""
        await self.client.post(
            f"/api/v1/attendances/sessions/{session_id}/message/",
            json={"role": role, "content": content, "message_type": "text"},
        )

    async def register_action(
        self,
        session_id: str,
        action_type: str,
        description: str,
        metadata: dict | None = None,
    ) -> None:
        """POST /sessions/{id}/action/"""
        await self.client.post(
            f"/api/v1/attendances/sessions/{session_id}/action/",
            json={
                "action_type": action_type,
                "description": description,
                "metadata": metadata or {},
            },
        )

    async def close(self, session_id: str, reason: str = "resolved", summary: str = "") -> None:
        """POST /sessions/{id}/close/"""
        await self.client.post(
            f"/api/v1/attendances/sessions/{session_id}/close/",
            json={"reason": reason, "summary": summary},
        )

    async def escalate(self, session_id: str, reason: str = "") -> None:
        """POST /sessions/{id}/escalate/"""
        await self.client.post(
            f"/api/v1/attendances/sessions/{session_id}/escalate/",
            json={"reason": reason},
        )
