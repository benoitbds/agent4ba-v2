"""FastAPI application for Agent4BA."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from agent4ba.ai.graph import app as workflow_app
from agent4ba.api.app_factory import create_app
from agent4ba.api.auth import get_current_user, router as auth_router
from agent4ba.api.event_queue import cleanup_event_queue, get_event_queue
from agent4ba.api.events import (
    AgentPlanEvent,
    AgentStartEvent,
    ErrorEvent,
    ImpactPlanReadyEvent,
    ThreadIdEvent,
    ToolUsedEvent,
    UserRequestEvent,
    WorkflowCompleteEvent,
)
from agent4ba.api.schemas import (
    ApprovalRequest,
    ChatRequest,
    ChatResponse,
    CreateProjectRequest,
    CreateWorkItemRequest,
    UpdateWorkItemRequest,
)
from agent4ba.core.document_ingestion import DocumentIngestionService
from agent4ba.core.logger import setup_logger
from agent4ba.core.models import User
from agent4ba.core.storage import ProjectContextService

# Configurer le logger
logger = setup_logger(__name__)

app = FastAPI(
    title="Agent4BA V2",
    description="Backend pour la gestion de backlog assistée par IA",
    version="0.1.0",
)

# Création de l'application via la factory
# La configuration CORS et autres middlewares sont gérés dans app_factory.py
app = create_app()

# Enregistrer le router d'authentification
app.include_router(auth_router)


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
    # LOG DEBUG 1/3: Afficher le corps complet de la requête
    logger.debug(f"[DEBUG] Received request body: {request.model_dump()}")

    # Générer un thread_id unique pour cette conversation
    thread_id = str(uuid.uuid4())

    print(f"[STREAMING] Starting stream for thread_id: {thread_id}")
    print(f"[STREAMING] Project: {request.project_id}, Query: {request.query}")

    # Liste pour accumuler tous les événements de cette session pour l'historique
    timeline_events: list[dict[str, Any]] = []

    try:
        # Envoyer immédiatement le thread_id au client
        thread_id_event = ThreadIdEvent(thread_id=thread_id)
        yield f"data: {thread_id_event.model_dump_json()}\n\n"
        timeline_events.append(thread_id_event.model_dump())
        print("[STREAMING] Sent thread_id event")

        # Créer la queue d'événements pour ce thread
        loop = asyncio.get_running_loop()
        event_queue = get_event_queue(thread_id, loop)
        print("[STREAMING] Created event queue")

        # Envoyer la requête de l'utilisateur comme premier événement
        user_request_event = UserRequestEvent(query=request.query)
        yield f"data: {user_request_event.model_dump_json()}\n\n"
        timeline_events.append(user_request_event.model_dump())

        # Préparer l'état initial pour le graphe
        # Convertir le context en liste de dictionnaires si présent
        context_list = None
        if request.context:
            context_list = [item.model_dump() for item in request.context]

        initial_state: dict[str, Any] = {
            "project_id": request.project_id,
            "user_query": request.query,
            "document_content": request.document_content or "",
            "context": context_list,
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

        # LOG DEBUG 2/3: Afficher l'état initial passé au graphe
        logger.debug(f"[DEBUG] Initial state passed to graph: {initial_state}")

        # Configuration pour LangGraph avec thread_id
        config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

        # Variables pour accumuler l'état
        accumulated_state: dict[str, Any] = initial_state.copy()

        print("[STREAMING] Starting workflow execution")

        # Générateur pour streamer les événements de la queue
        async def stream_queue_events():
            """Stream les événements de la queue au fur et à mesure."""
            print("[STREAMING] stream_queue_events started")
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
                    event_str = f"data: {agent_start_event.model_dump_json()}\n\n"
                    yield event_str
                    timeline_events.append(agent_start_event.model_dump())

                elif event_type == "agent_plan":
                    agent_plan_event = AgentPlanEvent(
                        steps=agent_event_data["steps"],
                        agent_name=agent_event_data["agent_name"],
                    )
                    event_str = f"data: {agent_plan_event.model_dump_json()}\n\n"
                    yield event_str
                    timeline_events.append(agent_plan_event.model_dump())

                elif event_type == "tool_used":
                    tool_used_event = ToolUsedEvent(
                        tool_run_id=agent_event_data["tool_run_id"],
                        tool_name=agent_event_data["tool_name"],
                        tool_icon=agent_event_data["tool_icon"],
                        description=agent_event_data["description"],
                        status=agent_event_data["status"],
                        details=agent_event_data.get("details"),
                    )
                    event_str = f"data: {tool_used_event.model_dump_json()}\n\n"
                    yield event_str
                    timeline_events.append(tool_used_event.model_dump())
            print(f"[STREAMING] stream_queue_events finished with {event_count} events")

        # Tâche pour exécuter le workflow LangGraph en arrière-plan
        async def run_langgraph_workflow():
            """Exécute le workflow LangGraph et met à jour l'état accumulé."""
            nonlocal accumulated_state
            print("[STREAMING] run_langgraph_workflow started")

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

                print(f"[STREAMING] run_langgraph_workflow finished with {event_count} events")
            except Exception as e:
                print(f"[STREAMING] Error in run_langgraph_workflow: {e}")
                import traceback
                traceback.print_exc()
                raise
            finally:
                # Signaler la fin du workflow à la queue
                print("[STREAMING] Signaling queue done")
                event_queue.done()

        # Lancer le workflow en tâche de fond
        print("[STREAMING] Starting LangGraph workflow task")
        workflow_task = asyncio.create_task(run_langgraph_workflow())

        # Streamer les événements de la queue au fur et à mesure
        print("[STREAMING] Starting to stream queue events")
        async for event_data in stream_queue_events():
            yield event_data

        # Attendre que le workflow soit terminé
        print("[STREAMING] Waiting for workflow task to complete")
        await workflow_task
        print("[STREAMING] Workflow task completed")

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
            timeline_events.append(impact_plan_event.model_dump())
            print("[STREAMING] Sent impact_plan_ready event")
        else:
            # Sinon, envoyer WorkflowCompleteEvent
            complete_event = WorkflowCompleteEvent(
                result=result if result else "Workflow completed",
                status=status,
            )
            yield f"data: {complete_event.model_dump_json()}\n\n"
            timeline_events.append(complete_event.model_dump())
            print("[STREAMING] Sent workflow_complete event")

        # Sauvegarder les événements dans l'historique de la timeline
        storage = ProjectContextService()
        storage.save_timeline_events(request.project_id, timeline_events)
        print(f"[STREAMING] Saved {len(timeline_events)} events to timeline history")

        print("[STREAMING] Stream completed successfully")

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
        timeline_events.append(error_event.model_dump())

        # Même en cas d'erreur, sauvegarder les événements
        try:
            storage = ProjectContextService()
            storage.save_timeline_events(request.project_id, timeline_events)
            print(
                f"[STREAMING] Saved {len(timeline_events)} events to "
                "timeline history (after error)"
            )
        except Exception as save_error:
            # Log l'erreur mais ne pas interrompre le flux
            print(f"Failed to save timeline events: {save_error}")
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
async def list_projects(
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """
    Liste tous les projets disponibles.

    Args:
        current_user: Utilisateur authentifié (injecté par la dépendance)

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


@app.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: str) -> None:
    """
    Supprime un projet et toutes ses données associées.

    Args:
        project_id: Identifiant unique du projet à supprimer

    Returns:
        Aucun contenu (code 204)

    Raises:
        HTTPException: Si le projet n'existe pas (404) ou si le project_id est invalide (400)
    """
    storage = ProjectContextService()

    try:
        storage.delete_project_data(project_id)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found: {e}",
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid project_id: {e}",
        ) from e


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


@app.get("/projects/{project_id}/timeline")
async def get_project_timeline(project_id: str) -> JSONResponse:
    """
    Récupère l'historique complet de la timeline d'un projet.

    Args:
        project_id: Identifiant unique du projet

    Returns:
        JSONResponse avec l'historique des sessions d'événements

    Raises:
        HTTPException: Si le projet n'existe pas
    """
    storage = ProjectContextService()

    try:
        history = storage.load_timeline_history(project_id)
        return JSONResponse(content=history)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading timeline history for project '{project_id}': {e}",
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
            detail=(
                f"Type de fichier non supporté: {file.content_type}. "
                "Seuls les fichiers PDF sont acceptés."
            ),
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


@app.delete("/projects/{project_id}/documents/{document_name}", status_code=204)
async def delete_project_document(project_id: str, document_name: str) -> None:
    """
    Supprime un document spécifique d'un projet et ses vecteurs associés.

    Cette opération :
    1. Valide les paramètres pour éviter les failles de sécurité (path traversal)
    2. Supprime le fichier physique (PDF/texte) du disque
    3. Supprime les chunks et vecteurs associés de la base vectorielle FAISS
    4. Sauvegarde l'index FAISS mis à jour

    Args:
        project_id: Identifiant unique du projet
        document_name: Nom du document à supprimer

    Returns:
        Aucun contenu (code 204)

    Raises:
        HTTPException: Si le projet n'existe pas (404), si le document n'existe pas (404)
                      ou si les paramètres sont invalides (400)
    """
    storage = ProjectContextService()
    project_dir = storage.base_path / project_id

    # Vérifier que le projet existe
    if not project_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found",
        )

    try:
        # Utiliser le service d'ingestion pour supprimer le document
        ingestion_service = DocumentIngestionService(project_id)
        ingestion_service.delete_document(document_name)

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{document_name}' not found in project '{project_id}': {e}",
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document_name: {e}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting document '{document_name}': {e}",
        ) from e


@app.post("/projects/{project_id}/work_items", status_code=201)
async def create_work_item(
    project_id: str,
    request: CreateWorkItemRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """
    Crée un nouveau WorkItem dans le backlog d'un projet.

    Args:
        project_id: Identifiant unique du projet
        request: Requête contenant les données du WorkItem à créer
        current_user: Utilisateur authentifié (injecté par la dépendance)

    Returns:
        JSONResponse avec le WorkItem créé et un statut 201 Created

    Raises:
        HTTPException: Si le projet n'existe pas
    """
    storage = ProjectContextService()

    try:
        # Créer le WorkItem avec les données de la requête
        item_data = request.model_dump(exclude_unset=True)
        new_item = storage.create_work_item_in_backlog(project_id, item_data)
        return JSONResponse(content=new_item.model_dump(), status_code=201)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Project not found: {e}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating WorkItem: {e}",
        ) from e


@app.put("/projects/{project_id}/work_items/{item_id}")
async def update_work_item(
    project_id: str,
    item_id: str,
    request: UpdateWorkItemRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """
    Met à jour un WorkItem dans le backlog d'un projet.

    Args:
        project_id: Identifiant unique du projet
        item_id: Identifiant du WorkItem à mettre à jour
        request: Requête contenant les données du WorkItem à mettre à jour
        current_user: Utilisateur authentifié (injecté par la dépendance)

    Returns:
        JSONResponse avec le WorkItem mis à jour

    Raises:
        HTTPException: Si le projet ou le WorkItem n'existe pas
    """
    storage = ProjectContextService()

    try:
        # Convertir la requête en dictionnaire en excluant les champs non définis
        item_data = request.model_dump(exclude_unset=True)

        # Le validation_status doit être human_validated car c'est un humain qui modifie
        item_data["validation_status"] = "human_validated"

        updated_item = storage.update_work_item_in_backlog(project_id, item_id, item_data)
        return JSONResponse(content=updated_item.model_dump())
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Project or WorkItem not found: {e}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating WorkItem '{item_id}': {e}",
        ) from e


@app.delete("/projects/{project_id}/work_items/{item_id}", status_code=204)
async def delete_work_item(
    project_id: str,
    item_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """
    Supprime un WorkItem du backlog d'un projet.

    Args:
        project_id: Identifiant unique du projet
        item_id: Identifiant du WorkItem à supprimer
        current_user: Utilisateur authentifié (injecté par la dépendance)

    Returns:
        Aucun contenu (code 204)

    Raises:
        HTTPException: Si le projet ou le WorkItem n'existe pas
    """
    storage = ProjectContextService()

    try:
        storage.delete_work_item_from_backlog(project_id, item_id)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Project or WorkItem not found: {e}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting WorkItem '{item_id}': {e}",
        ) from e


@app.put("/projects/{project_id}/backlog/{item_id}")
async def update_work_item_legacy(
    project_id: str, item_id: str, item_data: dict
) -> JSONResponse:
    """
    Met à jour un WorkItem dans le backlog d'un projet (endpoint legacy).

    DEPRECATED: Utiliser /projects/{project_id}/work_items/{item_id} à la place.

    Args:
        project_id: Identifiant unique du projet
        item_id: Identifiant du WorkItem à mettre à jour
        item_data: Données partielles du WorkItem à mettre à jour

    Returns:
        JSONResponse avec le WorkItem mis à jour

    Raises:
        HTTPException: Si le projet ou le WorkItem n'existe pas
    """
    storage = ProjectContextService()

    try:
        updated_item = storage.update_work_item_in_backlog(project_id, item_id, item_data)
        return JSONResponse(content=updated_item.model_dump())
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Project or WorkItem not found: {e}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating WorkItem '{item_id}': {e}",
        ) from e


@app.post("/projects/{project_id}/backlog/{item_id}/validate")
async def validate_work_item(project_id: str, item_id: str) -> JSONResponse:
    """
    Valide un WorkItem dans le backlog d'un projet (marque comme validé par un humain).

    Args:
        project_id: Identifiant unique du projet
        item_id: Identifiant du WorkItem à valider

    Returns:
        JSONResponse avec le WorkItem validé

    Raises:
        HTTPException: Si le projet ou le WorkItem n'existe pas
    """
    storage = ProjectContextService()

    try:
        validated_item = storage.validate_work_item_in_backlog(project_id, item_id)
        return JSONResponse(content=validated_item.model_dump())
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Project or WorkItem not found: {e}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error validating WorkItem '{item_id}': {e}",
        ) from e


@app.post("/projects/{project_id}/work_items/{item_id}/generate-acceptance-criteria")
async def generate_acceptance_criteria_for_item(
    project_id: str, item_id: str
) -> JSONResponse:
    """
    Génère les critères d'acceptation pour un WorkItem spécifique.

    Cette opération appelle directement l'agent de génération de critères d'acceptation
    sans passer par le graphe complet. Les critères générés sont automatiquement
    appliqués au WorkItem.

    Args:
        project_id: Identifiant unique du projet
        item_id: Identifiant du WorkItem pour lequel générer les critères

    Returns:
        JSONResponse avec le WorkItem mis à jour incluant les critères d'acceptation

    Raises:
        HTTPException: Si le projet ou le WorkItem n'existe pas, ou en cas d'erreur
    """
    from agent4ba.ai import backlog_agent

    # Créer un état minimal pour l'agent
    state: dict[str, Any] = {
        "project_id": project_id,
        "intent_args": {"work_item_id": item_id},
        "thread_id": "",  # Pas de thread_id nécessaire pour un appel direct
    }

    try:
        # Appeler la fonction de génération de critères d'acceptation
        result = backlog_agent.generate_acceptance_criteria(state)

        # Vérifier le statut de la réponse
        if result.get("status") == "error":
            raise HTTPException(
                status_code=400,
                detail=result.get("result", "Error generating acceptance criteria"),
            )

        # Récupérer l'ImpactPlan
        impact_plan = result.get("impact_plan", {})
        modified_items = impact_plan.get("modified_items", [])

        if not modified_items:
            raise HTTPException(
                status_code=500,
                detail="No modifications generated by the agent",
            )

        # Extraire le WorkItem modifié (le premier dans la liste)
        modification = modified_items[0]
        item_after = modification.get("after")

        if not item_after:
            raise HTTPException(
                status_code=500,
                detail="Invalid impact plan structure",
            )

        # Appliquer la modification en utilisant le storage service
        storage = ProjectContextService()
        updated_item = storage.update_work_item_in_backlog(
            project_id,
            item_id,
            {
                "acceptance_criteria": item_after["acceptance_criteria"],
                "validation_status": item_after["validation_status"],
            },
        )

        return JSONResponse(content=updated_item.model_dump())

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Project or WorkItem not found: {e}",
        ) from e
    except HTTPException:
        # Re-raise les HTTPException déjà créées
        raise
    except Exception as e:
        logger.error(
            f"Error generating acceptance criteria for item {item_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error generating acceptance criteria: {e}",
        ) from e
