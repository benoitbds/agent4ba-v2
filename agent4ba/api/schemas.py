"""API schemas for Agent4BA."""

from typing import Any

from pydantic import BaseModel, Field


class ContextItem(BaseModel):
    """Item de contexte pour cibler des documents ou work items spécifiques."""

    type: str = Field(..., description="Type de contexte: 'document' ou 'work_item'")
    id: str = Field(..., description="Identifiant du document ou du work item")


class ChatRequest(BaseModel):
    """Requête de chat pour l'interaction avec l'agent."""

    project_id: str = Field(..., description="Identifiant du projet")
    query: str = Field(..., description="Question ou commande de l'utilisateur")
    document_content: str | None = Field(
        None, description="Contenu optionnel d'un document à analyser"
    )
    context: list[ContextItem] | None = Field(
        None, description="Contexte optionnel (documents ou work items ciblés)"
    )
    session_id: str | None = Field(
        None,
        description="Identifiant de session pour le streaming temps réel des événements",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "project_id": "demo",
                    "query": "Liste les user stories du backlog",
                }
            ]
        }
    }


class ChatResponse(BaseModel):
    """Réponse du chat."""

    result: str = Field(..., description="Résultat de l'exécution")
    project_id: str = Field(..., description="Identifiant du projet")
    status: str | None = Field(None, description="Statut du workflow")
    thread_id: str | None = Field(
        None,
        description="Identifiant de conversation pour reprendre le workflow",
    )
    impact_plan: dict[str, Any] | None = Field(
        None,
        description="Plan d'impact en attente de validation (si workflow interrompu)",
    )


class ApprovalRequest(BaseModel):
    """Requête d'approbation ou de rejet d'un ImpactPlan."""

    approved: bool = Field(..., description="True pour approuver, False pour rejeter")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "approved": True,
                }
            ]
        }
    }


class CreateProjectRequest(BaseModel):
    """Requête de création d'un nouveau projet."""

    project_id: str = Field(..., description="Identifiant unique du projet")


class CreateWorkItemRequest(BaseModel):
    """Requête de création d'un nouveau WorkItem."""

    type: str = Field(..., description="Type de work item (story, task, bug, etc.)")
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
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Attributs additionnels (priority, status, etc.)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "story",
                    "title": "Implémenter l'authentification utilisateur",
                    "description": "En tant qu'utilisateur, je veux me connecter...",
                    "parent_id": None,
                    "acceptance_criteria": ["L'utilisateur peut se connecter avec email et mot de passe"],
                    "attributes": {
                        "priority": "high",
                        "status": "todo",
                        "points": 8,
                    },
                }
            ]
        }
    }


class UpdateWorkItemRequest(BaseModel):
    """Requête de mise à jour d'un WorkItem existant."""

    type: str | None = Field(None, description="Type de work item (story, task, bug, etc.)")
    title: str | None = Field(None, description="Titre du work item")
    description: str | None = Field(None, description="Description détaillée")
    parent_id: str | None = Field(
        None,
        description="Identifiant du parent (pour les hiérarchies)",
    )
    acceptance_criteria: list[str] | None = Field(
        None,
        description="Liste des critères d'acceptation pour ce work item",
    )
    attributes: dict[str, Any] | None = Field(
        None,
        description="Attributs additionnels (priority, status, etc.)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Implémenter l'authentification utilisateur (mise à jour)",
                    "attributes": {
                        "priority": "critical",
                        "status": "in_progress",
                    },
                }
            ]
        }
    }


class ClarificationResponse(BaseModel):
    """Réponse de l'utilisateur à une demande de clarification."""

    conversation_id: str = Field(
        ...,
        description="Identifiant de la conversation en attente de clarification",
    )
    user_response: str = Field(..., description="Réponse de l'utilisateur à la question")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                    "user_response": "pour FIR-3",
                }
            ]
        }
    }


class ClarificationNeededResponse(BaseModel):
    """Réponse indiquant qu'une clarification est nécessaire."""

    status: str = Field(
        default="clarification_needed",
        description="Statut indiquant qu'une clarification est nécessaire",
    )
    conversation_id: str = Field(
        ...,
        description="Identifiant unique de la conversation",
    )
    question: str = Field(
        ...,
        description="Question à poser à l'utilisateur pour clarifier sa demande",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "clarification_needed",
                    "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                    "question": "Pour quel work item souhaitez-vous générer les cas de test ?",
                }
            ]
        }
    }
