"""FastAPI application for Agent4BA."""

import shutil
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import JSONResponse, StreamingResponse

from agent4ba.ai.graph import app as workflow_app
from agent4ba.api.app_factory import create_app
from agent4ba.api.events import (
    ErrorEvent,
    ImpactPlanReadyEvent,
    NodeEndEvent,
    NodeStartEvent,
    ThreadIdEvent,
    WorkflowCompleteEvent,
)
from agent4ba.api.schemas import ApprovalRequest, ChatRequest, ChatResponse
from agent4ba.core.document_ingestion import DocumentIngestionService
from agent4ba.core.storage import ProjectContextService

app = FastAPI(
    title="Agent4BA V2",
    description="Backend pour la gestion de backlog assistée par IA",
    version="0.1.0",
)
from agent4ba.core.storage import ProjectContextService

# Création de l'application via la factory
# La configuration CORS et autres middlewares sont gérés dans app_factory.py
app = create_app()


@app.get("/health")
async def health_check() -> JSONResponse:
    """
    Point de contrôle de santé de l'API.

    Returns:
        JSONResponse avec le statut de l'application
    """
    return JSONResponse(content={"status": "ok"})


async def event_stream(request: ChatRequest) -> AsyncIterator[str]:
    """
    Générateur async qui yield des événements SSE du workflow.

    Args:
        request: Requête contenant project_id et query

    Yields:
        Chaînes formatées en SSE (data: {...}\\n\\n)
    """
    # Générer un thread_id unique pour cette conversation
    thread_id = str(uuid.uuid4())

    try:
        # Envoyer immédiatement le thread_id au client
        thread_id_event = ThreadIdEvent(thread_id=thread_id)
        yield f"data: {thread_id_event.model_dump_json()}\n\n"

        # Préparer l'état initial pour le graphe
        initial_state: dict[str, Any] = {
            "project_id": request.project_id,
            "user_query": request.query,
            "document_content": request.document_content or "",
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

        # Variables pour accumuler l'état
        accumulated_state: dict[str, Any] = initial_state.copy()

        # Utiliser astream_events pour obtenir tous les événements du graphe
        async for event in workflow_app.astream_events(
            initial_state,
            config,  # type: ignore[arg-type]
            version="v2",
        ):
            event_kind = event.get("event")
            event_data: dict[str, Any] = event.get("data", {})  # type: ignore[assignment]

            # Événement de début de nœud
            if event_kind == "on_chain_start":
                node_name = event.get("name", "")
                if node_name and node_name != "LangGraph":
                    start_event = NodeStartEvent(node_name=node_name)
                    yield f"data: {start_event.model_dump_json()}\n\n"

            # Événement de fin de nœud avec output
            elif event_kind == "on_chain_end":
                node_name = event.get("name", "")
                output = event_data.get("output")
                if node_name and node_name != "LangGraph":
                    # Mettre à jour l'état accumulé avec la sortie du nœud
                    if isinstance(output, dict):
                        accumulated_state.update(output)
                        # Ne générer un NodeEndEvent que si la sortie est un dictionnaire
                        # (les routeurs retournent des strings, on les filtre)
                        end_event = NodeEndEvent(node_name=node_name, output=output)
                        yield f"data: {end_event.model_dump_json()}\n\n"

        # Après avoir parcouru tous les événements, envoyer l'événement final
        result = accumulated_state.get("result", "")
        status = accumulated_state.get("status", "completed")
        impact_plan = accumulated_state.get("impact_plan", {})

        # Si le workflow attend une approbation, envoyer ImpactPlanReadyEvent
        if status == "awaiting_approval" and impact_plan:
            impact_plan_event = ImpactPlanReadyEvent(
                impact_plan=impact_plan,
                thread_id=thread_id,
                status=status,
            )
            yield f"data: {impact_plan_event.model_dump_json()}\n\n"
        else:
            # Sinon, envoyer WorkflowCompleteEvent
            complete_event = WorkflowCompleteEvent(
                result=result if result else "Workflow completed",
                status=status,
            )
            yield f"data: {complete_event.model_dump_json()}\n\n"

    except Exception as e:
        # En cas d'erreur, envoyer un ErrorEvent
        error_event = ErrorEvent(
            error=str(e),
            details="An error occurred during workflow execution",
        )
        yield f"data: {error_event.model_dump_json()}\n\n"


@app.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """
    Endpoint de chat pour interagir avec l'agent via SSE streaming.

    Args:
        request: Requête contenant project_id et query

    Returns:
        StreamingResponse avec événements SSE
    """
    return StreamingResponse(
        event_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Désactive le buffering nginx
        },
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


@app.get("/projects")
async def list_projects() -> JSONResponse:
    """
    Liste tous les projets disponibles.

    Returns:
        JSONResponse avec la liste des identifiants de projets

    """
    storage = ProjectContextService()
    projects_dir = storage.base_path

    # Créer le répertoire s'il n'existe pas
    projects_dir.mkdir(parents=True, exist_ok=True)

    # Scanner les sous-répertoires
    project_ids = []
    for entry in projects_dir.iterdir():
        if entry.is_dir():
            project_ids.append(entry.name)

    # Trier par ordre alphabétique
    project_ids.sort()

    return JSONResponse(content=project_ids)


@app.post("/projects")
async def create_project(request: CreateProjectRequest) -> JSONResponse:
    """
    Crée un nouveau projet.

    Args:
        request: Requête contenant l'identifiant du projet à créer

    Returns:
        JSONResponse avec l'identifiant du projet créé

    Raises:
        HTTPException: Si le projet existe déjà
    """
    storage = ProjectContextService()
    projects_dir = storage.base_path
    project_path = projects_dir / request.project_id

    # Vérifier si le projet existe déjà
    if project_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Project '{request.project_id}' already exists",
        )

    # Créer le répertoire du projet
    project_path.mkdir(parents=True, exist_ok=True)

    # Initialiser un backlog vide
    storage.save_backlog(request.project_id, [])

    return JSONResponse(
        content={"project_id": request.project_id, "message": "Project created successfully"},
        status_code=201,
    )


@app.get("/projects/{project_id}/backlog")
async def get_project_backlog(project_id: str) -> JSONResponse:
    """
    Récupère le backlog actuel d'un projet.

    Args:
        project_id: Identifiant unique du projet

    Returns:
        JSONResponse avec la liste des work items du backlog

    Raises:
        HTTPException: Si le projet n'existe pas ou n'a pas de backlog
    """
    storage = ProjectContextService()

    try:
        work_items = storage.load_context(project_id)
        # Convertir les WorkItem en dictionnaires
        items_data = [item.model_dump() for item in work_items]
        return JSONResponse(content=items_data)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Backlog not found for project '{project_id}': {e}",
        ) from e


@app.post("/projects/{project_id}/documents")
async def upload_document(project_id: str, file: UploadFile = File(...)) -> JSONResponse:
    """
    Upload et ingestion d'un document PDF dans le système RAG.

    Cette route :
    1. Reçoit un fichier PDF uploadé
    2. Le sauvegarde dans le répertoire documents du projet
    3. Lance le processus d'ingestion (extraction, vectorisation, indexation)

    Args:
        project_id: Identifiant unique du projet
        file: Fichier PDF uploadé

    Returns:
        JSONResponse avec les informations sur l'ingestion

    Raises:
        HTTPException: Si l'upload ou l'ingestion échoue
    """
    # Valider que c'est bien un fichier PDF
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported",
        )

    try:
        # Créer le service d'ingestion
        ingestion_service = DocumentIngestionService(project_id)

        # Définir le chemin de destination du fichier
        file_path = ingestion_service.documents_dir / file.filename

        # Sauvegarder le fichier uploadé
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Lancer l'ingestion du document
        result = ingestion_service.ingest_document(file_path, file.filename)

        return JSONResponse(
            content={
                "message": "Document ingested successfully",
                "filename": file.filename,
                "details": result,
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ingest document: {e}",
        ) from e
