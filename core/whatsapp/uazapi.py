"""Provider UazAPI — WhatsApp não oficial (Whatsmeow)."""
from __future__ import annotations

import httpx
import structlog
from core.settings import settings
from core.whatsapp.base import WhatsAppProvider

logger = structlog.get_logger()


class UazAPIProvider(WhatsAppProvider):

    async def send_text(self, phone: str, text: str, instance_token: str = "") -> None:
        url = f"{settings.uazapi_base_url}/message/sendText/{instance_token or settings.uazapi_global_token}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                url,
                json={"number": phone, "text": text},
                headers={"token": settings.uazapi_global_token},
            )
            resp.raise_for_status()

    def extract_phone(self, payload: dict) -> str | None:
        msg = payload.get("message", {})
        # sender_pn é o número real do usuário (ex: 5521974021620@s.whatsapp.net)
        sender = msg.get("sender_pn") or msg.get("chatid") or ""
        return sender.split("@")[0] if "@" in sender else sender or None

    def extract_text(self, payload: dict) -> str | None:
        msg = payload.get("message", {})
        # UazAPI envia o texto normalizado diretamente em message.text
        return msg.get("text") or None

    def extract_message_type(self, payload: dict) -> str:
        msg = payload.get("message", {})
        msg_type = msg.get("type", "")
        media_type = msg.get("mediaType", "")

        if msg_type == "text":
            return "text"
        if media_type in ("audio", "ptt", "image", "document", "sticker"):
            return media_type
        if msg_type in ("audio", "ptt", "image", "document", "sticker"):
            return msg_type
        return "unknown"

    def extract_media_url(self, payload: dict) -> str | None:
        msg = payload.get("message", {})
        return msg.get("mediaUrl") or None

    def extract_mime_type(self, payload: dict) -> str:
        msg = payload.get("message", {})
        return msg.get("mimetype", "")

    def extract_contact_name(self, payload: dict) -> str:
        chat = payload.get("chat", {})
        msg = payload.get("message", {})
        # chat.name é o nome salvo nos contatos; senderName como fallback
        return chat.get("name") or msg.get("senderName") or ""

    def extract_instance_token(self, payload: dict) -> str | None:
        # UazAPI envia o token da instância no campo raiz "token"
        return payload.get("token") or None