"""API schemas for Agent4BA."""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Requête de chat pour l'interaction avec l'agent."""

    project_id: str = Field(..., description="Identifiant du projet")
    query: str = Field(..., description="Question ou commande de l'utilisateur")
    document_content: str | None = Field(
        None, description="Contenu optionnel d'un document à analyser"
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
