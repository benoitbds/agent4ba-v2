"""Configuration centrale de l'application Agent4BA."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Paramètres de configuration de l'application.

    Les variables sont lues depuis les variables d'environnement ou un fichier .env.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Configuration CORS
    # Note: Les listes doivent être fournies au format JSON dans les variables d'environnement
    # Exemple: CORS_ALLOWED_ORIGINS='["http://localhost:3000", "http://192.168.1.95:3000"]'
    CORS_ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",  # Frontend Next.js (port par défaut)
        "http://localhost:3001",  # Frontend Next.js (port alternatif)
    ]


# Instance unique des paramètres pour toute l'application
settings = Settings()
