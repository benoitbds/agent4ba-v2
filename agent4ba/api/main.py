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
        "next_node": "",
        "agent_task": "",
        "impact_plan": {},
        "status": "",
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

    # Extraire les informations finales
    result = accumulated_state.get("result", "")
    status = accumulated_state.get("status", "completed")
    impact_plan = accumulated_state.get("impact_plan", {})

    # Si le workflow est en attente de validation, retourner l'ImpactPlan
    if status == "awaiting_approval" and impact_plan:
        return ChatResponse(
            result=result if result else "ImpactPlan generated, awaiting approval",
            project_id=request.project_id,
            status=status,
            impact_plan=impact_plan,
        )

    # Sinon, retourner le résultat normal
    return ChatResponse(
        result=result if result else "Workflow completed without result",
        project_id=request.project_id,
        status=status,
        impact_plan=None,
    )
