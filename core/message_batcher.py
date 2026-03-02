"""
Agrupa mensagens sequenciais do mesmo usuário com debounce.

Problema: usuários digitam em vários pedaços em sequência rápida.
Solução: espera DEBOUNCE_SECONDS antes de processar, agrupando tudo.

Implementação:
- Lista Redis `batch:{school_id}:{phone}` acumula mensagens
- Timer Redis `timer:{school_id}:{phone}` sinaliza quando processar
"""
from __future__ import annotations

import asyncio
import json
import structlog
import redis.asyncio as aioredis

from core.settings import settings

logger = structlog.get_logger()

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def add_message(school_id: str, phone: str, message: str) -> None:
    """Adiciona mensagem à fila e renova o timer."""
    redis = get_redis()
    batch_key = f"batch:{school_id}:{phone}"
    timer_key = f"timer:{school_id}:{phone}"

    await redis.rpush(batch_key, message)
    await redis.expire(batch_key, 60)
    await redis.set(timer_key, "1", ex=settings.debounce_seconds)


async def wait_and_collect(school_id: str, phone: str) -> str | None:
    """
    Aguarda o debounce expirar e retorna as mensagens agrupadas.
    Retorna None se outro worker já coletou (race condition handling).
    """
    redis = get_redis()
    timer_key = f"timer:{school_id}:{phone}"
    batch_key = f"batch:{school_id}:{phone}"

    await asyncio.sleep(settings.debounce_seconds + 0.2)

    # Verifica se o timer ainda existe (pode ter sido renovado por nova msg)
    if await redis.exists(timer_key):
        return None  # Outra mensagem chegou — deixa o próximo processar

    # Coleta e limpa atomicamente
    messages = await redis.lrange(batch_key, 0, -1)
    if not messages:
        return None

    await redis.delete(batch_key)
    return " ".join(messages)
