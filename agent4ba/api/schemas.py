"""API schemas for Agent4BA."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Requête de chat pour l'interaction avec l'agent."""

    project_id: str = Field(..., description="Identifiant du projet")
    query: str = Field(..., description="Question ou commande de l'utilisateur")

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
