"""Retorna o provider WhatsApp correto conforme configuração da escola."""
from __future__ import annotations

from core.whatsapp.base import WhatsAppProvider
from core.whatsapp.uazapi import UazAPIProvider
from core.whatsapp.meta import MetaCloudProvider


def get_provider(school: dict) -> WhatsAppProvider:
    """
    school = resultado do school_resolver: {school_id, school_name, sa_token, whatsapp_provider, ...}
    """
    provider_type = school.get("whatsapp_provider", "uazapi")

    if provider_type == "meta":
        return MetaCloudProvider(
            access_token=school.get("meta_access_token", ""),
            phone_number_id=school.get("meta_phone_number_id", ""),
        )

    return UazAPIProvider()
