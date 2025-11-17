"""Project schema models for meta-modelable backlog.

Ce module définit les modèles pour le schéma de projet dynamique.
Le schéma permet de définir les types de WorkItems et leurs champs
de manière flexible, permettant à l'IA de modifier la structure
sur demande de l'utilisateur.
"""

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class FieldDefinition(BaseModel):
    """Définition d'un champ dans un type de WorkItem."""

    name: str = Field(..., description="Nom du champ (ex: 'title', 'priority')")
    type: str = Field(
        ...,
        description="Type du champ (ex: 'text', 'textarea', 'select', 'date', 'number', 'boolean', 'list')",
    )
    label: str | None = Field(
        None,
        description="Label affiché dans l'UI (ex: 'Titre', 'Priorité')",
    )
    required: bool = Field(
        default=False,
        description="Indique si le champ est obligatoire",
    )
    options: List[str] | None = Field(
        None,
        description="Options possibles pour les champs de type 'select' (ex: ['low', 'medium', 'high'])",
    )
    default: Any | None = Field(
        None,
        description="Valeur par défaut du champ",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "priority",
                    "type": "select",
                    "label": "Priorité",
                    "required": False,
                    "options": ["low", "medium", "high"],
                    "default": "medium",
                },
                {
                    "name": "title",
                    "type": "text",
                    "label": "Titre",
                    "required": True,
                },
                {
                    "name": "description",
                    "type": "textarea",
                    "label": "Description",
                    "required": False,
                },
            ]
        }
    }


class WorkItemTypeDefinition(BaseModel):
    """Définition d'un type de WorkItem."""

    name: str = Field(
        ...,
        description="Nom du type (ex: 'feature', 'story', 'bug', 'task')",
    )
    label: str | None = Field(
        None,
        description="Label affiché dans l'UI (ex: 'Feature', 'User Story', 'Bug')",
    )
    fields: List[FieldDefinition] = Field(
        default_factory=list,
        description="Liste des champs de ce type de WorkItem",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "story",
                    "label": "User Story",
                    "fields": [
                        {
                            "name": "title",
                            "type": "text",
                            "label": "Titre",
                            "required": True,
                        },
                        {
                            "name": "description",
                            "type": "textarea",
                            "label": "Description",
                            "required": False,
                        },
                        {
                            "name": "priority",
                            "type": "select",
                            "label": "Priorité",
                            "options": ["low", "medium", "high"],
                            "default": "medium",
                        },
                    ],
                }
            ]
        }
    }


class ProjectSchema(BaseModel):
    """Schéma complet d'un projet définissant tous les types de WorkItems possibles."""

    version: str = Field(
        default="1.0",
        description="Version du schéma (pour évolution future)",
    )
    work_item_types: List[WorkItemTypeDefinition] = Field(
        ...,
        description="Liste des types de WorkItems définis pour ce projet",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "version": "1.0",
                    "work_item_types": [
                        {
                            "name": "feature",
                            "label": "Feature",
                            "fields": [
                                {
                                    "name": "title",
                                    "type": "text",
                                    "label": "Titre",
                                    "required": True,
                                },
                                {
                                    "name": "description",
                                    "type": "textarea",
                                    "label": "Description",
                                },
                            ],
                        },
                        {
                            "name": "story",
                            "label": "User Story",
                            "fields": [
                                {
                                    "name": "title",
                                    "type": "text",
                                    "label": "Titre",
                                    "required": True,
                                },
                            ],
                        },
                    ],
                }
            ]
        }
    }
