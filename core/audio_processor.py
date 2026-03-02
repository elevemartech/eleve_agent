"""
Transcrição de áudio com OpenAI Whisper.

Custo: ~$0.006/minuto.
Formatos aceitos: ogg, mp3, mp4, m4a, wav, webm.
"""
from __future__ import annotations

import httpx
import structlog
from openai import AsyncOpenAI

from core.settings import settings

logger = structlog.get_logger()
_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def transcribe(audio_url: str, mime_type: str = "audio/ogg") -> str:
    """
    Baixa o áudio da URL e transcreve com Whisper.

    Retorna: "[Áudio]: {texto transcrito}"
    """
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.get(audio_url)
        resp.raise_for_status()
        audio_bytes = resp.content

    ext = mime_type.split("/")[-1].replace("mpeg", "mp3").replace("ogg", "ogg")
    filename = f"audio.{ext}"

    try:
        result = await get_client().audio.transcriptions.create(
            model=settings.openai_model_audio,
            file=(filename, audio_bytes, mime_type),
            language="pt",
        )
        text = result.text.strip()
        logger.info("audio_transcribed", chars=len(text))
        return f"[Áudio]: {text}"
    except Exception as e:
        logger.error("audio_transcription_error", error=str(e))
        return "[Áudio]: (não foi possível transcrever)"
