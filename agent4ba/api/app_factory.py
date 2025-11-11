"""Factory pour créer et configurer l'application FastAPI."""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from agent4ba.core.config import settings

# Taille maximale autorisée pour les uploads : 50 Mo
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 Mo en bytes


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """
    Middleware pour limiter la taille maximale du corps des requêtes HTTP.

    Rejette les requêtes dont le Content-Length dépasse MAX_UPLOAD_SIZE
    avec une erreur HTTP 413 (Content Too Large).
    """

    async def dispatch(self, request: Request, call_next):
        """Vérifie la taille du corps de la requête avant de la traiter."""
        content_length = request.headers.get("content-length")

        if content_length:
            content_length_int = int(content_length)
            if content_length_int > MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"Request body too large. Maximum size is {MAX_UPLOAD_SIZE} bytes (50 MB).",
                )

        return await call_next(request)


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

    # Middleware pour limiter la taille des uploads à 50 Mo
    app.add_middleware(MaxBodySizeMiddleware)

    # Configuration CORS avec les origines depuis la configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],  # Autorise toutes les méthodes (GET, POST, etc.)
        allow_headers=["*"],  # Autorise tous les headers
    )

    return app
