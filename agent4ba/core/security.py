"""Security utilities for project-level authorization in Agent4BA."""

from typing import Annotated

from fastapi import Depends, HTTPException, Path, status

from agent4ba.api.auth import get_current_user
from agent4ba.core.models import User
from agent4ba.core.storage import ProjectContextService


async def get_current_project_user(
    project_id: Annotated[str, Path(..., description="Identifiant unique du projet")],
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dépendance pour vérifier que l'utilisateur authentifié a accès au projet spécifié.

    Cette fonction récupère le project_id depuis les path parameters et vérifie,
    via le ProjectContextService, si l'utilisateur authentifié est bien autorisé
    pour ce project_id.

    Args:
        project_id: Identifiant du projet (extrait automatiquement du path)
        current_user: Utilisateur authentifié (injecté par get_current_user)

    Returns:
        L'objet utilisateur s'il est autorisé pour ce projet

    Raises:
        HTTPException: 403 Forbidden si l'utilisateur n'a pas accès au projet
    """
    # Vérifier si l'utilisateur est autorisé pour ce projet
    project_service = ProjectContextService()

    if not project_service.is_user_authorized_for_project(project_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.username}' is not authorized to access project '{project_id}'",
        )

    return current_user
