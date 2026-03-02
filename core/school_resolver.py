"""
Resolve a escola a partir do messaging_token da instância WhatsApp.

Cache Redis de 1 hora para evitar chamadas repetidas à API.
"""
from __future__ import annotations

import json
import structlog
import redis.asyncio as aioredis

from core.settings import settings
from core.api_client import DjangoAPIClient

logger = structlog.get_logger()

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def resolve_school(messaging_token: str) -> dict | None:
    """
    Retorna dados da escola pelo token da instância WhatsApp.

    Retorno:
        {
            "school_id": str,
            "school_name": str,
            "sa_token": str,
            "whatsapp_provider": "uazapi" | "meta",
        }
    """
    cache_key = f"school:{messaging_token}"
    redis = get_redis()

    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    client = DjangoAPIClient(token=settings.system_sa_token)
    try:
        data = await client.get(
            "/api/v1/schools/resolve/",
            params={"messaging_token": messaging_token},
        )
    except Exception as e:
        logger.error("school_resolve_error", token=messaging_token[-6:], error=str(e))
        return None

    if not data:
        return None

    school_data = {
        "school_id": str(data["id"]),
        "school_name": data["school_name"],
        "sa_token": data["sa_token"],
        "whatsapp_provider": data.get("whatsapp_provider", "uazapi"),
    }

    await redis.set(cache_key, json.dumps(school_data), ex=3600)
    logger.info("school_resolved", school=school_data["school_name"])
    return school_data
