"""Data models for Agent4BA."""

import uuid
from typing import Any, List, Literal

from pydantic import BaseModel, Field


class User(BaseModel):
    """Représente un utilisateur du système."""

    id: str = Field(..., description="Identifiant unique de l'utilisateur (UUID)")
    username: str = Field(..., description="Nom d'utilisateur unique")
    hashed_password: str = Field(..., description="Mot de passe hashé")
    is_active: bool = Field(default=True, description="Indique si l'utilisateur est actif")
    project_ids: List[str] = Field(
        default_factory=list,
        description="Liste des identifiants de projets auxquels l'utilisateur est associé",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "username": "john_doe",
                    "hashed_password": "$2b$12$...",
                    "is_active": True,
                    "project_ids": ["project-1", "project-2"],
                }
            ]
        }
    }


class TestCaseStep(BaseModel):
    """Représente une étape d'un cas de test."""

    step: str = Field(..., description="Description of the action to perform.")
    expected_result: str = Field(..., description="The expected outcome of the action.")


class TestCase(BaseModel):
    """Représente un cas de test structuré."""

    title: str = Field(..., description="A concise title for the test case.")
    scenario: str = Field(
        ...,
        description="The user scenario being tested, often in Gherkin format (Given/When/Then).",
    )
    steps: List[TestCaseStep] = Field(
        default_factory=list,
        description="A list of detailed steps for the test case.",
    )


class Diagram(BaseModel):
    """Représente un diagramme Mermaid.js."""

    id: str = Field(
        default_factory=lambda: f"diag_{uuid.uuid4().hex[:8]}",
        description="Identifiant unique du diagramme",
    )
    title: str = Field(..., description="Titre du diagramme")
    code: str = Field(..., description="Code Mermaid.js du diagramme")


class WorkItem(BaseModel):
    """Représente un élément de travail (user story, task, bug, test_case, etc.)."""

    id: str = Field(..., description="Identifiant unique du work item")
    project_id: str = Field(..., description="Identifiant du projet associé")
    type: Literal["feature", "story", "task", "bug", "epic", "test_case"] = Field(
        ..., description="Type de work item"
    )
    title: str = Field(..., description="Titre du work item")
    description: str | None = Field(None, description="Description détaillée")
    parent_id: str | None = Field(
        None,
        description="Identifiant du parent (pour les hiérarchies)",
    )
    acceptance_criteria: list[str] = Field(
        default_factory=list,
        description="Liste des critères d'acceptation pour ce work item",
    )
    scenario: str | None = Field(
        None,
        description="Scénario de test au format Gherkin (pour les test_case uniquement)",
    )
    steps: list[TestCaseStep] = Field(
        default_factory=list,
        description="Liste des étapes détaillées du cas de test (pour les test_case uniquement)",
    )
    diagrams: list[Diagram] = Field(
        default_factory=list,
        description="Liste des diagrammes associés à ce work item",
    )
    validation_status: Literal["ia_generated", "human_validated", "ia_modified"] = Field(
        default="ia_generated",
        description="Statut de validation (ia_generated pour les items créés par l'IA, human_validated pour les items validés, ia_modified pour les items validés puis modifiés par l'IA)",
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
                    "validation_status": "ia_generated",
                    "attributes": {
                        "priority": "high",
                        "status": "todo",
                        "points": 8,
                    },
                }
            ]
        }
    }
