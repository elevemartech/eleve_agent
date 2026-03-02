from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Eleve API
    django_api_url: str = "http://localhost:8000"
    system_sa_token: str = ""

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_model_vision: str = "gpt-4o"
    openai_model_audio: str = "whisper-1"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # WhatsApp — UazAPI
    uazapi_base_url: str = "https://eleve.uazapi.com"
    uazapi_global_token: str = ""

    # WhatsApp — Meta
    meta_verify_token: str = ""
    meta_app_secret: str = ""

    # Comportamento
    debounce_seconds: int = 3
    environment: str = "development"
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
