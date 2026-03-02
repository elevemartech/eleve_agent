"""
Análise de imagens com GPT-4o Vision.

Custo: ~$0.005/imagem.
Identifica: boletos, documentos, comprovantes, circulares, fotos gerais.
"""
from __future__ import annotations

import base64
import httpx
import structlog
from openai import AsyncOpenAI

from core.settings import settings

logger = structlog.get_logger()
_client: AsyncOpenAI | None = None

VISION_PROMPT = """Analise esta imagem enviada por um responsável escolar via WhatsApp.
Identifique o tipo e extraia as informações mais relevantes de forma concisa:

- Boleto bancário: informe vencimento, valor e código de barras se visível
- Comprovante de pagamento: informe valor, data e beneficiário
- Documento de identidade: informe apenas o tipo (não transcreva dados pessoais)
- Circular ou comunicado escolar: transcreva o conteúdo principal
- Foto ou imagem genérica: descreva brevemente o que mostra

Responda de forma direta e objetiva, em português."""


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def analyze(image_url: str) -> str:
    """
    Baixa a imagem e analisa com GPT-4o Vision.

    Retorna: "[Imagem]: {descrição}"
    """
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.get(image_url)
        resp.raise_for_status()
        image_b64 = base64.b64encode(resp.content).decode()
        content_type = resp.headers.get("content-type", "image/jpeg")

    try:
        result = await get_client().chat.completions.create(
            model=settings.openai_model_vision,
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{content_type};base64,{image_b64}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
        )
        description = result.choices[0].message.content.strip()
        logger.info("image_analyzed", chars=len(description))
        return f"[Imagem]: {description}"
    except Exception as e:
        logger.error("image_analysis_error", error=str(e))
        return "[Imagem]: (não foi possível analisar)"
