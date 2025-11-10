"""FastAPI application for Agent4BA."""

import asyncio
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
from agent4ba.api.event_queue import cleanup_event_queue, get_event_queue
from agent4ba.api.events import (
    AgentPlanEvent,
    AgentStartEvent,
    ErrorEvent,
    ImpactPlanReadyEvent,
    NodeEndEvent,
    NodeStartEvent,
    ThreadIdEvent,
    ToolUsedEvent,
    WorkflowCompleteEvent,
)
from agent4ba.api.main_streaming import merge_streams
from agent4ba.api.schemas import (
    ApprovalRequest,
    ChatRequest,
    ChatResponse,
    CreateProjectRequest,
)
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

    print(f"[STREAMING] Starting stream for thread_id: {thread_id}")
    print(f"[STREAMING] Project: {request.project_id}, Query: {request.query}")

    try:
        # Envoyer immédiatement le thread_id au client
        thread_id_event = ThreadIdEvent(thread_id=thread_id)
        yield f"data: {thread_id_event.model_dump_json()}\n\n"
        print(f"[STREAMING] Sent thread_id event")

        # Créer la queue d'événements pour ce thread
        loop = asyncio.get_running_loop()
        event_queue = get_event_queue(thread_id, loop)
        print(f"[STREAMING] Created event queue")

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
            "agent_events": [],
            "thread_id": thread_id,  # Passer le thread_id dans le state
        }

        # Configuration pour LangGraph avec thread_id
        config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

        # Variables pour accumuler l'état
        accumulated_state: dict[str, Any] = initial_state.copy()

        print(f"[STREAMING] Starting workflow execution")

        # Générateur pour streamer les événements de la queue
        async def stream_queue_events():
            """Stream les événements de la queue au fur et à mesure."""
            print(f"[STREAMING] stream_queue_events started")
            event_count = 0
            async for agent_event_data in event_queue.get_events():
                event_count += 1
                event_type = agent_event_data.get("type")
                print(f"[STREAMING] Received event #{event_count}: {event_type}")

                if event_type == "agent_start":
                    agent_start_event = AgentStartEvent(
                        thought=agent_event_data["thought"],
                        agent_name=agent_event_data["agent_name"],
                    )
                    yield f"data: {agent_start_event.model_dump_json()}\n\n"

                elif event_type == "agent_plan":
                    agent_plan_event = AgentPlanEvent(
                        steps=agent_event_data["steps"],
                        agent_name=agent_event_data["agent_name"],
                    )
                    yield f"data: {agent_plan_event.model_dump_json()}\n\n"

                elif event_type == "tool_used":
                    tool_used_event = ToolUsedEvent(
                        tool_name=agent_event_data["tool_name"],
                        tool_icon=agent_event_data["tool_icon"],
                        description=agent_event_data["description"],
                        status=agent_event_data["status"],
                        details=agent_event_data.get("details"),
                    )
                    yield f"data: {tool_used_event.model_dump_json()}\n\n"
            print(f"[STREAMING] stream_queue_events finished with {event_count} events")

        # Générateur pour streamer les événements LangGraph
        async def stream_langgraph_events():
            """Stream les événements du workflow LangGraph."""
            nonlocal accumulated_state
            print(f"[STREAMING] stream_langgraph_events started")

            try:
                event_count = 0
                async for event in workflow_app.astream_events(
                    initial_state,
                    config,  # type: ignore[arg-type]
                    version="v2",
                ):
                    event_count += 1
                    event_kind = event.get("event")
                    event_data: dict[str, Any] = event.get("data", {})  # type: ignore[assignment]

                    if event_count % 10 == 0:
                        print(f"[STREAMING] Processed {event_count} LangGraph events")

                    # Événement de fin de nœud avec output
                    if event_kind == "on_chain_end":
                        node_name = event.get("name", "")
                        output = event_data.get("output")
                        if node_name and node_name != "LangGraph":
                            print(f"[STREAMING] Node finished: {node_name}")
                            # Mettre à jour l'état accumulé avec la sortie du nœud
                            if isinstance(output, dict):
                                accumulated_state.update(output)

                print(f"[STREAMING] stream_langgraph_events finished with {event_count} events")
            except Exception as e:
                print(f"[STREAMING] Error in stream_langgraph_events: {e}")
                import traceback
                traceback.print_exc()
                raise
            finally:
                # Signaler la fin du workflow à la queue
                print(f"[STREAMING] Signaling queue done")
                event_queue.done()

        # Merger les deux streams et les yielder
        print(f"[STREAMING] Starting merge_streams")
        async for event_data in merge_streams(
            stream_queue_events(),
            stream_langgraph_events(),
        ):
            yield event_data

        print(f"[STREAMING] Merge complete, sending final events")

        # Après avoir parcouru tous les événements, envoyer l'événement final
        result = accumulated_state.get("result", "")
        status = accumulated_state.get("status", "completed")
        impact_plan = accumulated_state.get("impact_plan", {})

        print(f"[STREAMING] Final status: {status}")

        # Si le workflow attend une approbation, envoyer ImpactPlanReadyEvent
        if status == "awaiting_approval" and impact_plan:
            impact_plan_event = ImpactPlanReadyEvent(
                impact_plan=impact_plan,
                thread_id=thread_id,
                status=status,
            )
            yield f"data: {impact_plan_event.model_dump_json()}\n\n"
            print(f"[STREAMING] Sent impact_plan_ready event")
        else:
            # Sinon, envoyer WorkflowCompleteEvent
            complete_event = WorkflowCompleteEvent(
                result=result if result else "Workflow completed",
                status=status,
            )
            yield f"data: {complete_event.model_dump_json()}\n\n"
            print(f"[STREAMING] Sent workflow_complete event")

        print(f"[STREAMING] Stream completed successfully")

    except Exception as e:
        # En cas d'erreur, envoyer un ErrorEvent
        print(f"[STREAMING] Error occurred: {e}")
        import traceback
        traceback.print_exc()

        error_event = ErrorEvent(
            error=str(e),
            details="An error occurred during workflow execution",
        )
        yield f"data: {error_event.model_dump_json()}\n\n"
    finally:
        # Nettoyer la queue d'événements
        print(f"[STREAMING] Cleaning up queue for thread_id: {thread_id}")
        cleanup_event_queue(thread_id)


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


@app.get("/projects/{project_id}/documents")
async def list_project_documents(project_id: str) -> JSONResponse:
    """
    Liste les documents d'un projet.

    Args:
        project_id: Identifiant unique du projet

    Returns:
        JSONResponse avec la liste des noms de fichiers

    Raises:
        HTTPException: Si le projet n'existe pas
    """
    storage = ProjectContextService()
    documents_dir = storage.base_path / project_id / "documents"

    # Créer le répertoire s'il n'existe pas
    documents_dir.mkdir(parents=True, exist_ok=True)

    # Scanner les fichiers
    document_names = []
    for file_path in documents_dir.iterdir():
        if file_path.is_file():
            document_names.append(file_path.name)

    # Trier par ordre alphabétique
    document_names.sort()

    return JSONResponse(content=document_names)


@app.post("/projects/{project_id}/documents")
async def upload_project_document(
    project_id: str,
    file: UploadFile = File(...),
) -> JSONResponse:
    """
    Upload un document pour un projet et le vectorise automatiquement.

    Args:
        project_id: Identifiant unique du projet
        file: Fichier à uploader

    Returns:
        JSONResponse avec les détails de l'upload et de la vectorisation

    Raises:
        HTTPException: Si le type de fichier n'est pas supporté ou si la vectorisation échoue
    """
    # Vérifier le type de fichier
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non supporté: {file.content_type}. Seuls les fichiers PDF sont acceptés.",
        )

    storage = ProjectContextService()
    documents_dir = storage.base_path / project_id / "documents"

    # Créer le répertoire s'il n'existe pas
    documents_dir.mkdir(parents=True, exist_ok=True)

    # Sauvegarder le fichier
    file_path = documents_dir / file.filename

    try:
        # Lire et écrire le fichier
        content = await file.read()
        with file_path.open("wb") as f:
            f.write(content)

        # Vectoriser le document automatiquement
        ingestion_service = DocumentIngestionService(project_id)
        ingestion_result = ingestion_service.ingest_document(file_path, file.filename)

        return JSONResponse(
            content={
                "filename": file.filename,
                "message": f"Fichier '{file.filename}' uploadé et vectorisé avec succès",
                "vectorization": {
                    "num_chunks": ingestion_result["num_chunks"],
                    "num_pages": ingestion_result["num_pages"],
                    "status": ingestion_result["status"],
                },
            },
            status_code=201,
        )
    except Exception as e:
        # Si la vectorisation échoue, supprimer le fichier uploadé
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'upload ou de la vectorisation du fichier: {e}",
        ) from e
