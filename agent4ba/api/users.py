"""User management endpoints for Agent4BA."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from agent4ba.api.auth import get_current_user
from agent4ba.api.schemas_auth import UserResponse
from agent4ba.core.models import User
from agent4ba.services.user_service import UserService

# Configuration du logger
logger = logging.getLogger(__name__)

# Instance du service utilisateur
user_service = UserService()

# Router pour les endpoints de gestion des utilisateurs
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/search", response_model=list[UserResponse])
async def search_users(
    query: Annotated[str, Query(min_length=1, description="Chaîne de recherche pour filtrer les utilisateurs")],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[UserResponse]:
    """
    Recherche des utilisateurs par nom d'utilisateur.

    Cet endpoint permet de rechercher des utilisateurs existants dans le système
    en filtrant par nom d'utilisateur (insensible à la casse).

    Args:
        query: Chaîne de caractères à rechercher dans les noms d'utilisateurs
        current_user: Utilisateur authentifié (injecté par la dépendance)

    Returns:
        Liste des utilisateurs dont le username contient la chaîne query
    """
    logger.info(f"User {current_user.username} searching for users with query: {query}")

    # Rechercher les utilisateurs
    users = user_service.search_users(query)

    # Convertir en UserResponse (sans les mots de passe hashés)
    user_responses = [
        UserResponse(id=user.id, username=user.username)
        for user in users
    ]

    logger.info(f"Found {len(user_responses)} users matching query: {query}")
    return user_responses
