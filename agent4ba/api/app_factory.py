"""Factory pour créer et configurer l'application FastAPI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent4ba.core.config import settings


def create_app() -> FastAPI:
    """
    Crée et configure l'instance FastAPI de l'application.

    Cette fonction centralise la configuration de l'application,
    y compris les middlewares et les paramètres CORS.

    Returns:
        Instance configurée de l'application FastAPI
    """
    app = FastAPI(
        title="Agent4BA V2",
        description="Backend pour la gestion de backlog assistée par IA",
        version="0.1.0",
    )

    # Configuration CORS avec les origines depuis la configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],  # Autorise toutes les méthodes (GET, POST, etc.)
        allow_headers=["*"],  # Autorise tous les headers
    )

    return app
