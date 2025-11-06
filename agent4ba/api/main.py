"""FastAPI application for Agent4BA."""

from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from agent4ba.ai.graph import app as workflow_app
from agent4ba.api.schemas import ChatRequest, ChatResponse

app = FastAPI(
    title="Agent4BA V2",
    description="Backend pour la gestion de backlog assistée par IA",
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> JSONResponse:
    """
    Point de contrôle de santé de l'API.

    Returns:
        JSONResponse avec le statut de l'application
    """
    return JSONResponse(content={"status": "ok"})


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Endpoint de chat pour interagir avec l'agent.

    Args:
        request: Requête contenant project_id et query

    Returns:
        Réponse contenant le résultat de l'exécution
    """
    # Préparer l'état initial pour le graphe
    initial_state: dict[str, Any] = {
        "project_id": request.project_id,
        "user_query": request.query,
        "intent": {},
        "result": "",
    }

    # Exécuter le graphe en mode streaming
    accumulated_state: dict[str, Any] = initial_state.copy()
    for state_update in workflow_app.stream(initial_state):
        # state_update est un dict avec les nœuds comme clés
        # et leurs mises à jour comme valeurs
        for _, node_updates in state_update.items():
            if isinstance(node_updates, dict):
                accumulated_state.update(node_updates)

    # Extraire le résultat final
    result = accumulated_state.get("result", "")

    return ChatResponse(
        result=result if result else "Workflow completed without result",
        project_id=request.project_id,
    )
