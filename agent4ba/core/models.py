"""Data models for Agent4BA."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class User(BaseModel):
    """Représente un utilisateur du système."""

    id: str = Field(..., description="Identifiant unique de l'utilisateur (UUID)")
    username: str = Field(..., description="Nom d'utilisateur unique")
    hashed_password: str = Field(..., description="Mot de passe hashé")
    is_active: bool = Field(default=True, description="Indique si l'utilisateur est actif")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "username": "john_doe",
                    "hashed_password": "$2b$12$...",
                    "is_active": True,
                }
            ]
        }
    }


class WorkItem(BaseModel):
    """Représente un élément de travail (user story, task, bug, etc.)."""

    id: str = Field(..., description="Identifiant unique du work item")
    project_id: str = Field(..., description="Identifiant du projet associé")
    type: str = Field(..., description="Type de work item (story, task, bug, etc.)")
    title: str = Field(..., description="Titre du work item")
    description: str | None = Field(None, description="Description détaillée")
    parent_id: str | None = Field(
        None,
        description="Identifiant du parent (pour les hiérarchies)",
    )
    validation_status: Literal["pending_validation", "human_validated"] = Field(
        default="human_validated",
        description="Statut de validation (pending_validation pour les items générés par l'IA, human_validated pour les items validés)",
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Attributs additionnels (priority, status, etc.)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "WI-001",
                    "project_id": "PRJ-001",
                    "type": "story",
                    "title": "Implémenter l'authentification utilisateur",
                    "description": "En tant qu'utilisateur, je veux me connecter...",
                    "parent_id": None,
                    "validation_status": "human_validated",
                    "attributes": {
                        "priority": "high",
                        "status": "todo",
                        "points": 8,
                    },
                }
            ]
        }
    }
