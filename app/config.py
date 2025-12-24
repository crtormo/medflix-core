"""
Configuración centralizada usando Pydantic Settings.
Carga automáticamente desde variables de entorno y archivo .env
"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración de la aplicación MedFlix."""
    
    # Base de Datos
    postgres_user: str = "medflix"
    postgres_password: str = "medflix_secret"
    postgres_host: str = "db"
    postgres_port: str = "5432"
    postgres_db: str = "medflix_db"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8005
    debug: bool = False
    
    # Servicios Externos
    groq_api_key: Optional[str] = None
    
    # Telegram
    telegram_api_id: Optional[str] = None
    telegram_api_hash: Optional[str] = None
    telegram_session_name: str = "medflix_userbot_session"
    
    # Scheduler
    scan_interval_hours: int = 12
    
    @property
    def database_url(self) -> str:
        """URL de conexión a PostgreSQL."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Retorna instancia cacheada de settings."""
    return Settings()
