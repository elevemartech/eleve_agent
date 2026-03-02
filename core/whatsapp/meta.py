"""Provider Meta Cloud API — WhatsApp Business oficial."""
from __future__ import annotations

import httpx
import structlog
from core.whatsapp.base import WhatsAppProvider

logger = structlog.get_logger()

META_API_URL = "https://graph.facebook.com/v20.0"


class MetaCloudProvider(WhatsAppProvider):

    def __init__(self, access_token: str, phone_number_id: str):
        self.access_token = access_token
        self.phone_number_id = phone_number_id

    async def send_text(self, phone: str, text: str, **kwargs) -> None:
        url = f"{META_API_URL}/{self.phone_number_id}/messages"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "text",
                    "text": {"body": text},
                },
            )
            resp.raise_for_status()

    def extract_phone(self, payload: dict) -> str | None:
        try:
            entry = payload["entry"][0]["changes"][0]["value"]
            return entry["messages"][0]["from"]
        except (KeyError, IndexError):
            return None

    def extract_text(self, payload: dict) -> str | None:
        try:
            msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]
            if msg["type"] == "text":
                return msg["text"]["body"]
        except (KeyError, IndexError):
            pass
        return None

    def extract_message_type(self, payload: dict) -> str:
        try:
            return payload["entry"][0]["changes"][0]["value"]["messages"][0]["type"]
        except (KeyError, IndexError):
            return "unknown"

    def extract_media_url(self, payload: dict) -> str | None:
        # Meta requer download separado via Graph API com o media_id
        try:
            msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]
            msg_type = msg["type"]
            if msg_type in ("audio", "image", "document"):
                return msg[msg_type].get("id")  # É o media_id, não URL direta
        except (KeyError, IndexError):
            pass
        return None

    def extract_mime_type(self, payload: dict) -> str:
        try:
            msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]
            msg_type = msg["type"]
            if msg_type in ("audio", "image", "document"):
                return msg[msg_type].get("mime_type", "")
        except (KeyError, IndexError):
            pass
        return ""

    def extract_contact_name(self, payload: dict) -> str:
        try:
            contacts = payload["entry"][0]["changes"][0]["value"].get("contacts", [])
            if contacts:
                return contacts[0].get("profile", {}).get("name", "")
        except (KeyError, IndexError):
            pass
        return ""

    def extract_instance_token(self, payload: dict) -> str | None:
        try:
            return payload["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
        except (KeyError, IndexError):
            return None
