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
        sender = payload.get("sender") or payload.get("from") or ""
        return sender.split("@")[0] if "@" in sender else sender or None

    def extract_text(self, payload: dict) -> str | None:
        msg = payload.get("message", {})
        return (
            msg.get("conversation")
            or msg.get("extendedTextMessage", {}).get("text")
            or None
        )

    def extract_message_type(self, payload: dict) -> str:
        msg = payload.get("message", {})
        if "conversation" in msg or "extendedTextMessage" in msg:
            return "text"
        if "audioMessage" in msg:
            return "audio"
        if "pttMessage" in msg:
            return "ptt"
        if "imageMessage" in msg:
            return "image"
        if "documentMessage" in msg:
            return "document"
        if "stickerMessage" in msg:
            return "sticker"
        return "unknown"

    def extract_media_url(self, payload: dict) -> str | None:
        msg = payload.get("message", {})
        for key in ("audioMessage", "pttMessage", "imageMessage", "documentMessage"):
            if key in msg:
                return msg[key].get("url")
        return None

    def extract_mime_type(self, payload: dict) -> str:
        msg = payload.get("message", {})
        for key in ("audioMessage", "pttMessage", "imageMessage", "documentMessage"):
            if key in msg:
                return msg[key].get("mimetype", "")
        return ""

    def extract_contact_name(self, payload: dict) -> str:
        return payload.get("pushName") or payload.get("notifyName") or ""

    def extract_instance_token(self, payload: dict) -> str | None:
        return payload.get("instance") or payload.get("instanceId") or None
