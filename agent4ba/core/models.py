"""Data models for Agent4BA."""

from typing import Any

from pydantic import BaseModel, Field


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
                    "attributes": {
                        "priority": "high",
                        "status": "todo",
                        "points": 8,
                    },
                }
            ]
        }
    }
