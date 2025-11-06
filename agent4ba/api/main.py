"""FastAPI application for Agent4BA."""

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from agent4ba.ai.graph import app as workflow_app
from agent4ba.api.schemas import ApprovalRequest, ChatRequest, ChatResponse

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
    # Générer un thread_id unique pour cette conversation
    thread_id = str(uuid.uuid4())

    # Préparer l'état initial pour le graphe
    initial_state: dict[str, Any] = {
        "project_id": request.project_id,
        "user_query": request.query,
        "intent": {},
        "next_node": "",
        "agent_task": "",
        "impact_plan": {},
        "status": "",
        "approval_decision": None,
        "result": "",
    }

    # Configuration pour LangGraph avec thread_id
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

    # Exécuter le graphe en mode streaming avec thread_id
    accumulated_state: dict[str, Any] = initial_state.copy()
    for state_update in workflow_app.stream(initial_state, config):  # type: ignore[arg-type]
        # state_update est un dict avec les nœuds comme clés
        # et leurs mises à jour comme valeurs
        for _, node_updates in state_update.items():
            if isinstance(node_updates, dict):
                accumulated_state.update(node_updates)

    # Extraire les informations finales
    result = accumulated_state.get("result", "")
    status = accumulated_state.get("status", "completed")
    impact_plan = accumulated_state.get("impact_plan", {})

    # Si le workflow est en attente de validation, retourner l'ImpactPlan avec thread_id
    if status == "awaiting_approval" and impact_plan:
        return ChatResponse(
            result=result if result else "ImpactPlan generated, awaiting approval",
            project_id=request.project_id,
            status=status,
            thread_id=thread_id,
            impact_plan=impact_plan,
        )

    # Sinon, retourner le résultat normal
    return ChatResponse(
        result=result if result else "Workflow completed without result",
        project_id=request.project_id,
        status=status,
        thread_id=None,
        impact_plan=None,
    )


@app.post("/agent/run/{thread_id}/continue", response_model=ChatResponse)
async def continue_workflow(thread_id: str, request: ApprovalRequest) -> ChatResponse:
    """
    Reprend un workflow interrompu avec une décision d'approbation.

    Args:
        thread_id: Identifiant du thread de conversation
        request: Décision d'approbation (approved: true/false)

    Returns:
        Réponse contenant le résultat final après approbation

    Raises:
        HTTPException: Si le thread_id n'existe pas ou le workflow n'est pas en pause
    """
    # Configuration pour reprendre le thread spécifique
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

    # Récupérer l'état actuel du workflow
    try:
        current_state = workflow_app.get_state(config)  # type: ignore[arg-type]
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Thread {thread_id} not found or expired: {e}",
        ) from e

    # Vérifier que le workflow est bien en pause
    if not current_state.next:
        raise HTTPException(
            status_code=400,
            detail="Workflow is not in a paused state (no next node to execute)",
        )

    # Mettre à jour l'état avec la décision d'approbation
    workflow_app.update_state(
        config,  # type: ignore[arg-type]
        {"approval_decision": request.approved},
    )

    # Reprendre l'exécution du workflow
    accumulated_state: dict[str, Any] = {}
    for state_update in workflow_app.stream(None, config):  # type: ignore[arg-type]
        # state_update est un dict avec les nœuds comme clés
        # et leurs mises à jour comme valeurs
        for _, node_updates in state_update.items():
            if isinstance(node_updates, dict):
                accumulated_state.update(node_updates)

    # Extraire les informations finales
    result = accumulated_state.get("result", "")
    status = accumulated_state.get("status", "completed")
    project_id = accumulated_state.get("project_id", "")

    return ChatResponse(
        result=result if result else "Workflow completed",
        project_id=project_id,
        status=status,
        thread_id=None,  # Le workflow est terminé, plus besoin du thread_id
        impact_plan=None,
    )
