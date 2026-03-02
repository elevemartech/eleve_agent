"""
Roteador central de mídia.

Normaliza áudio e imagem para texto antes de entrar no batcher.
O agente nunca sabe se a mensagem veio de um áudio ou imagem.
"""
from __future__ import annotations

import structlog
from core.audio_processor import transcribe
from core.image_processor import analyze

logger = structlog.get_logger()


async def process(message_type: str, media_url: str, mime_type: str = "") -> str | None:
    """
    Processa mídia e retorna texto normalizado.

    message_type: audio | ptt | image | document | sticker
    Retorna None para tipos não suportados (sticker, vídeo, etc).
    """
    if message_type in ("audio", "ptt"):
        return await transcribe(media_url, mime_type or "audio/ogg")

    if message_type == "image":
        return await analyze(media_url)

    if message_type == "document":
        logger.info("document_received_not_supported")
        return (
            "[Documento recebido] Ainda não processo documentos diretamente. "
            "Você pode descrever o que precisa ou tirar uma foto do documento?"
        )

    # sticker, video, location, reaction — ignora
    logger.info("media_type_ignored", message_type=message_type)
    return None
