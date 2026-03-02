"""Interface abstrata para providers WhatsApp."""
from __future__ import annotations
from abc import ABC, abstractmethod


class WhatsAppProvider(ABC):

    @abstractmethod
    async def send_text(self, phone: str, text: str) -> None:
        """Envia mensagem de texto."""

    @abstractmethod
    def extract_phone(self, payload: dict) -> str | None:
        """Extrai número do remetente do payload do webhook."""

    @abstractmethod
    def extract_text(self, payload: dict) -> str | None:
        """Extrai texto da mensagem (None se for mídia)."""

    @abstractmethod
    def extract_message_type(self, payload: dict) -> str:
        """Retorna: text | audio | ptt | image | document | sticker | ..."""

    @abstractmethod
    def extract_media_url(self, payload: dict) -> str | None:
        """URL do arquivo de mídia."""

    @abstractmethod
    def extract_mime_type(self, payload: dict) -> str:
        """MIME type da mídia (ex: audio/ogg)."""

    @abstractmethod
    def extract_contact_name(self, payload: dict) -> str:
        """Nome do contato (pushName ou nome cadastrado)."""

    @abstractmethod
    def extract_instance_token(self, payload: dict) -> str | None:
        """Token da instância — usado para identificar a escola."""
