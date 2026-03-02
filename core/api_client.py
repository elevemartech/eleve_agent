"""
Cliente HTTP assíncrono para a Eleve API (Django).

Todas as chamadas usam ServiceAccount (sa_token) — isolamento multi-tenant automático.
"""
from __future__ import annotations

import structlog
import httpx

from core.settings import settings

logger = structlog.get_logger()


class DjangoAPIClient:
    def __init__(self, token: str):
        self.base_url = settings.django_api_url.rstrip("/")
        self.headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
        }

    async def get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=self.headers, params=params)
            resp.raise_for_status()
            return resp.json()

    async def post(self, path: str, json: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=self.headers, json=json or {})
            resp.raise_for_status()
            return resp.json()

    async def patch(self, path: str, json: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.patch(url, headers=self.headers, json=json or {})
            resp.raise_for_status()
            return resp.json()
