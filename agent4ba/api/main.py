"""FastAPI application for Agent4BA."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import status

from agent4ba.api import app_context

from agent4ba.ai.graph import app as workflow_app
from agent4ba.api.app_factory import create_app
from agent4ba.api.auth import get_current_user, router as auth_router
from agent4ba.api.users import router as users_router
from agent4ba.api.event_queue import cleanup_event_queue, get_event_queue
from agent4ba.api.session_manager import get_session_manager
from agent4ba.api.timeline_service import get_timeline_service
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
    AddUserToProjectRequest,
    ApprovalRequest,
    ChatRequest,
    ChatResponse,
    ClarificationNeededResponse,
    ClarificationResponse,
    CreateProjectRequest,
    CreateWorkItemRequest,
    UpdateWorkItemRequest,
)
from agent4ba.core.document_ingestion import DocumentIngestionService
from agent4ba.core.logger import setup_logger
from agent4ba.core.models import User
from agent4ba.core.security import get_current_project_user
from agent4ba.core.storage import ProjectContextService
from agent4ba.services.user_service import UserService

# Configurer le logger
logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire du cycle de vie de l'application FastAPI.

    Capture la boucle d'événements asyncio au démarrage et la stocke
    dans le contexte applicatif global pour permettre les appels thread-safe
    dans les agents et services.
    """
    # Capture the event loop on startup
    app_context.EVENT_LOOP = asyncio.get_running_loop()
    logger.info("--- Event loop captured and stored in app_context ---")
    yield
    # Cleanup on shutdown (optional)
    app_context.EVENT_LOOP = None
    logger.info("--- Event loop released from app_context ---")


# Création de l'application via la factory avec le lifespan
# La configuration CORS et autres middlewares sont gérés dans app_factory.py
app = create_app(lifespan=lifespan)

# Enregistrer le router d'authentification
app.include_router(auth_router)

# Enregistrer le router de gestion des utilisateurs
app.include_router(users_router)


@app.get("/health")
async def health_check() -> JSONResponse:
    """
    Point de contrôle de santé de l'API.

    Returns:
        JSONResponse avec le statut de l'application
    """
    return JSONResponse(content={"status": "ok"})


@app.get("/timeline/stream/{session_id}")
async def stream_timeline_events(session_id: str) -> StreamingResponse:
    """
    Endpoint SSE pour streamer les événements de timeline d'une session.

    Ce endpoint permet au frontend de s'abonner à un flux d'événements
    correspondant à une session de traitement et d'afficher la progression
    du workflow agentique en temps réel.

    Args:
        session_id: Identifiant unique de la session (thread_id)

    Returns:
        StreamingResponse avec les événements au format SSE
    """
    timeline_service = get_timeline_service()
    logger.info(f"[TIMELINE_STREAM] Client connected for session: {session_id}")

    async def event_generator() -> AsyncIterator[str]:
        """Générateur d'événements SSE qui attend les événements de manière bloquante."""
        try:
            # Récupérer la queue pour cette session
            loop = asyncio.get_running_loop()
            queue = timeline_service.register_session_loop(session_id, loop)
            logger.info(f"[TIMELINE_STREAM] Queue registered for session: {session_id}")

            event_count = 0

            # Boucle qui attend indéfiniment les événements
            while True:
                # Attendre le prochain événement (bloquant)
                # Cette instruction fait une pause et attend indéfiniment s'il n'y a pas d'événements
                event = await queue.get()

                # Vérifier si c'est le signal de fin (sentinelle None)
                if event is None:
                    logger.info(
                        f"[TIMELINE_STREAM] Received sentinel (None) for session {session_id} "
                        f"after {event_count} events - ending stream"
                    )
                    break

                # C'est un événement normal, l'envoyer au client
                event_count += 1
                event_data = event.model_dump_json()
                sse_message = f"data: {event_data}\n\n"

                logger.debug(
                    f"[TIMELINE_STREAM] Sending event #{event_count} to session {session_id}: "
                    f"{event.type}"
                )
                yield sse_message

            # Envoyer le signal de fin au client UNIQUEMENT après la fin réelle du workflow
            yield "data: [DONE]\n\n"
            logger.info(f"[TIMELINE_STREAM] Sent [DONE] signal and closing stream for session {session_id}")

        except Exception as e:
            logger.error(
                f"[TIMELINE_STREAM] Error streaming events for session {session_id}: {e}",
                exc_info=True,
            )
            # Envoyer un événement d'erreur au client
            error_data = {
                "type": "error",
                "message": f"Stream error: {str(e)}",
                "status": "ERROR",
            }
            yield f"data: {error_data}\n\n"

        finally:
            # Optionnel : nettoyer la session après le stream
            # timeline_service.cleanup_session(session_id)
            logger.info(f"[TIMELINE_STREAM] Client disconnected from session: {session_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Désactive le buffering nginx
        },
    )


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
    # Liste pour accumuler tous les événements de cette session pour l'historique
    timeline_events: list[dict[str, Any]] = []

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

    # Ajouter le thread_id event
    thread_id_event = ThreadIdEvent(thread_id=thread_id)
    timeline_events.append(thread_id_event.model_dump())

    # Ajouter un événement pour indiquer la décision d'approbation
    approval_message = "Approved" if request.approved else "Rejected"
    user_request_event = UserRequestEvent(query=f"Approval decision: {approval_message}")
    timeline_events.append(user_request_event.model_dump())

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

    # Extraire les événements détaillés de l'agent depuis l'état accumulé
    agent_events = accumulated_state.get("agent_events", [])
    if agent_events:
        timeline_events.extend(agent_events)
        logger.info(f"[CONTINUE] Extracted {len(agent_events)} agent events from state")

    # Ajouter l'événement WorkflowCompleteEvent
    complete_event = WorkflowCompleteEvent(
        result=result if result else "Workflow completed",
        status=status,
    )
    timeline_events.append(complete_event.model_dump())

    # Sauvegarder les événements dans l'historique de la timeline
    if project_id:
        try:
            storage = ProjectContextService()
            storage.save_timeline_events(project_id, timeline_events)
            logger.info(f"[CONTINUE] Saved {len(timeline_events)} events to timeline history")
        except Exception as save_error:
            logger.error(f"Failed to save timeline events: {save_error}")

    return ChatResponse(
        result=result if result else "Workflow completed",
        project_id=project_id,
        status=status,
        thread_id=None,  # Le workflow est terminé, plus besoin du thread_id
        impact_plan=None,
    )


def run_workflow_in_background(
    session_id: str,
    project_id: str,
    query: str,
    document_content: str,
    context: list[dict[str, Any]] | None,
) -> None:
    """
    Fonction wrapper synchrone qui exécute le workflow LangGraph en arrière-plan.

    Cette fonction contient toute la logique d'exécution du workflow qui était
    auparavant dans le endpoint execute_workflow. Elle est exécutée dans une
    tâche de fond par FastAPI pour permettre le streaming temps réel via SSE.

    Args:
        session_id: Identifiant unique de la session
        project_id: Identifiant du projet
        query: Requête de l'utilisateur
        document_content: Contenu du document (optionnel)
        context: Contexte de la conversation (optionnel)
    """
    from agent4ba.api.timeline_service import TimelineEvent as TLEvent

    logger.info(f"[BACKGROUND] Starting workflow execution for session: {session_id}")

    # Récupérer les services nécessaires
    session_manager = get_session_manager()
    timeline_service = get_timeline_service()

    # Liste pour accumuler tous les événements de cette session pour l'historique
    timeline_events: list[dict[str, Any]] = []

    # Ajouter le thread_id event
    thread_id_event = ThreadIdEvent(thread_id=session_id)
    timeline_events.append(thread_id_event.model_dump())

    # Ajouter la requête de l'utilisateur
    user_request_event = UserRequestEvent(query=query)
    timeline_events.append(user_request_event.model_dump())

    # Préparer l'état initial pour le graphe
    initial_state: dict[str, Any] = {
        "project_id": project_id,
        "user_query": query,
        "document_content": document_content or "",
        "context": context,
        "intent": {},
        "next_node": "",
        "agent_task": "",
        "impact_plan": {},
        "status": "",
        "approval_decision": None,
        "result": "",
        "agent_events": [],
        "thread_id": session_id,
        "clarification_needed": False,
        "clarification_question": "",
        "user_response": "",
    }

    # Configuration pour LangGraph avec le session_id
    config: dict[str, Any] = {"configurable": {"thread_id": session_id}}

    try:
        # Pousser l'événement WORKFLOW_START immédiatement
        workflow_start = TLEvent(
            type="WORKFLOW_START",
            message=f"Processing query for project {project_id}",
            status="IN_PROGRESS",
        )
        timeline_service.add_event(session_id, workflow_start)
        logger.info("[BACKGROUND] Pushed WORKFLOW_START event")

        # Exécuter le workflow avec streaming pour pousser les événements en temps réel
        final_state: dict[str, Any] = {}
        processed_event_ids = set()  # Pour éviter les doublons

        logger.info("[BACKGROUND] Using stream() for real-time event pushing")
        for state_update in workflow_app.stream(initial_state, config):  # type: ignore[arg-type]
            # Accumuler l'état final
            for node_name, node_state in state_update.items():
                logger.info(f"[BACKGROUND] Processing node: {node_name}")

                if isinstance(node_state, dict):
                    final_state.update(node_state)

                    # Si des agent_events sont présents dans cette mise à jour, les pousser immédiatement
                    if "agent_events" in node_state and node_state["agent_events"]:
                        new_events = node_state["agent_events"]
                        logger.info(f"[BACKGROUND] Found {len(new_events)} agent_events in node {node_name}")

                        # Convertir et pousser uniquement les nouveaux événements
                        for event_data in new_events:
                            # Utiliser event_id pour détecter les doublons
                            event_id = event_data.get("event_id") or f"{event_data.get('type')}_{len(timeline_events)}"

                            if event_id not in processed_event_ids:
                                processed_event_ids.add(event_id)
                                timeline_events.append(event_data)

                                # Convertir en TimelineEvent et pousser au TimelineService
                                tl_event = TLEvent(
                                    type=event_data.get("type", "UNKNOWN"),
                                    message=event_data.get("message", ""),
                                    status=event_data.get("status", "IN_PROGRESS"),
                                    agent_name=event_data.get("agent_name"),
                                    details=event_data.get("details"),
                                )
                                timeline_service.add_event(session_id, tl_event)
                                logger.info(
                                    f"[BACKGROUND] Pushed event to TimelineService: {tl_event.type}"
                                )

        # Extraire tous les événements de l'état final pour l'historique
        agent_events = final_state.get("agent_events", [])
        if agent_events:
            # Ajouter uniquement les événements qui ne sont pas déjà dans timeline_events
            for event in agent_events:
                event_id = event.get("event_id") or f"{event.get('type')}_{len(timeline_events)}"
                if event_id not in processed_event_ids:
                    timeline_events.append(event)
            logger.info(f"[BACKGROUND] Extracted {len(agent_events)} total agent events from state")

        # Extraire le statut du workflow
        workflow_status = final_state.get("status", "completed")

        # Vérifier si une clarification est nécessaire
        if final_state.get("clarification_needed", False):
            clarification_question = final_state.get(
                "clarification_question", "Veuillez préciser votre demande."
            )
            logger.info(f"[BACKGROUND] Clarification needed: {clarification_question}")

            # Sauvegarder le checkpoint
            session_manager.save_checkpoint(session_id, final_state)

            # Ajouter un événement pour la clarification
            clarification_event = WorkflowCompleteEvent(
                result=clarification_question,
                status="clarification_needed",
            )
            timeline_events.append(clarification_event.model_dump())

            # Pousser l'événement de clarification au TimelineService
            clarification_tl_event = TLEvent(
                type="CLARIFICATION_NEEDED",
                message=clarification_question,
                status="WAITING",
            )
            timeline_service.add_event(session_id, clarification_tl_event)
            logger.info("[BACKGROUND] Pushed CLARIFICATION_NEEDED event")

            # Signaler la fin du stream (le workflow attend une réponse)
            timeline_service.signal_done(session_id)
            logger.info(f"[BACKGROUND] Signaled stream done (clarification needed) for session: {session_id}")

        # Si le workflow attend une approbation
        elif workflow_status == "awaiting_approval":
            logger.info("[BACKGROUND] Workflow awaiting approval (interrupted before approval node)")
            logger.info(f"[BACKGROUND] Thread ID for resuming: {session_id}")

            # Ajouter l'événement ImpactPlanReadyEvent
            impact_plan = final_state.get("impact_plan", {})
            impact_plan_event = ImpactPlanReadyEvent(
                impact_plan=impact_plan,
                thread_id=session_id,
                status=workflow_status,
            )
            timeline_events.append(impact_plan_event.model_dump())

            # Pousser l'événement d'approbation au TimelineService
            approval_tl_event = TLEvent(
                type="IMPACT_PLAN_READY",
                message="Impact plan ready for approval",
                status="WAITING",
                details={"impact_plan": impact_plan, "thread_id": session_id},
            )
            timeline_service.add_event(session_id, approval_tl_event)
            logger.info("[BACKGROUND] Pushed IMPACT_PLAN_READY event")

            # Signaler la fin du stream (le workflow attend une approbation)
            timeline_service.signal_done(session_id)
            logger.info(f"[BACKGROUND] Signaled stream done (approval needed) for session: {session_id}")

        else:
            # Workflow vraiment terminé
            # Nettoyer la session
            if session_manager.session_exists(session_id):
                session_manager.delete_session(session_id)

            # Ajouter l'événement WorkflowCompleteEvent
            result = final_state.get("result", "Workflow completed")
            complete_event = WorkflowCompleteEvent(
                result=result if result else "Workflow completed",
                status=workflow_status,
            )
            timeline_events.append(complete_event.model_dump())

            # Pousser l'événement WORKFLOW_COMPLETE au TimelineService
            workflow_complete = TLEvent(
                type="WORKFLOW_COMPLETE",
                message=f"Workflow completed with status: {workflow_status}",
                status="SUCCESS" if workflow_status != "error" else "ERROR",
            )
            timeline_service.add_event(session_id, workflow_complete)
            logger.info("[BACKGROUND] Pushed WORKFLOW_COMPLETE event")

            # Signaler la fin du stream
            timeline_service.signal_done(session_id)
            logger.info(f"[BACKGROUND] Signaled stream done for session: {session_id}")

        # Sauvegarder les événements dans l'historique de la timeline
        storage = ProjectContextService()
        storage.save_timeline_events(project_id, timeline_events)
        logger.info(f"[BACKGROUND] Saved {len(timeline_events)} events to timeline history")

        logger.info(f"[BACKGROUND] Workflow {session_id} finished with status: {workflow_status}")

    except Exception as e:
        logger.error(f"[BACKGROUND] Error during workflow execution: {e}", exc_info=True)

        # Signaler la fin du stream même en cas d'erreur
        timeline_service.signal_done(session_id)
        logger.info(f"[BACKGROUND] Signaled stream done after error for session: {session_id}")

        # Ajouter un événement d'erreur
        error_event = ErrorEvent(
            error=str(e),
            details="An error occurred during workflow execution",
        )
        timeline_events.append(error_event.model_dump())

        # Pousser l'événement d'erreur au TimelineService
        error_tl_event = TLEvent(
            type="ERROR",
            message=f"Workflow error: {str(e)}",
            status="ERROR",
        )
        timeline_service.add_event(session_id, error_tl_event)

        # Même en cas d'erreur, sauvegarder les événements
        try:
            storage = ProjectContextService()
            storage.save_timeline_events(project_id, timeline_events)
            logger.info(
                f"[BACKGROUND] Saved {len(timeline_events)} events to "
                "timeline history (after error)"
            )
        except Exception as save_error:
            logger.error(f"Failed to save timeline events: {save_error}")

        # Nettoyer la session en cas d'erreur
        if session_manager.session_exists(session_id):
            session_manager.delete_session(session_id)


@app.post("/execute")
async def execute_workflow(request: ChatRequest, background_tasks: BackgroundTasks) -> JSONResponse:
    """
    Lance l'exécution d'un workflow en tâche de fond et retourne immédiatement.

    Cet endpoint lance l'exécution du workflow en arrière-plan via BackgroundTasks
    et retourne immédiatement un session_id au client. Le client peut ensuite
    s'abonner au flux SSE via /timeline/stream/{session_id} pour recevoir
    les événements en temps réel au fur et à mesure de l'exécution.

    Args:
        request: Requête contenant project_id et query
        background_tasks: Gestionnaire de tâches de fond FastAPI

    Returns:
        HTTP 202 Accepted avec le session_id pour suivre l'exécution
    """
    logger.info(f"[EXECUTE] Starting workflow for project: {request.project_id}")
    logger.info(f"[EXECUTE] User query: {request.query}")

    # Utiliser le session_id fourni par le frontend ou générer un nouveau
    session_id = request.session_id if request.session_id else str(uuid.uuid4())
    logger.info(f"[EXECUTE] Using session_id: {session_id}")

    # Convertir le context en liste de dictionnaires si présent
    context_list = None
    if request.context:
        context_list = [item.model_dump() for item in request.context]

    # Ajouter la tâche de fond pour exécuter le workflow
    background_tasks.add_task(
        run_workflow_in_background,
        session_id=session_id,
        project_id=request.project_id,
        query=request.query,
        document_content=request.document_content or "",
        context=context_list,
    )
    logger.info(f"[EXECUTE] Background task added for session: {session_id}")

    # Retourner une réponse immédiate avec le session_id
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "message": "Workflow started",
            "session_id": session_id,
        },
    )


@app.post("/respond", response_model=ChatResponse)
async def respond_to_clarification(request: ClarificationResponse) -> ChatResponse:
    """
    Reprend un workflow interrompu après avoir reçu une réponse de l'utilisateur.

    Cet endpoint est appelé après qu'un workflow ait demandé une clarification
    via l'endpoint /execute. Il reprend l'exécution du workflow avec la réponse
    de l'utilisateur.

    Args:
        request: Requête contenant conversation_id et user_response

    Returns:
        Réponse contenant le résultat final du workflow

    Raises:
        HTTPException: Si le conversation_id n'existe pas ou en cas d'erreur
    """
    logger.info(f"[RESPOND] Resuming workflow for conversation: {request.conversation_id}")
    logger.info(f"[RESPOND] User response: {request.user_response}")

    # Liste pour accumuler tous les événements de cette session pour l'historique
    timeline_events: list[dict[str, Any]] = []

    session_manager = get_session_manager()

    # Vérifier que la session existe
    if not session_manager.session_exists(request.conversation_id):
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {request.conversation_id} not found or expired",
        )

    try:
        # Récupérer le checkpoint
        checkpoint = session_manager.get_checkpoint(request.conversation_id)

        # Ajouter le thread_id event
        thread_id_event = ThreadIdEvent(thread_id=request.conversation_id)
        timeline_events.append(thread_id_event.model_dump())

        # Ajouter la réponse de l'utilisateur comme événement
        user_request_event = UserRequestEvent(query=f"Clarification: {request.user_response}")
        timeline_events.append(user_request_event.model_dump())

        # Mettre à jour l'état avec la réponse de l'utilisateur
        checkpoint["user_response"] = request.user_response
        checkpoint["clarification_needed"] = False

        # Configuration pour reprendre le workflow
        config: dict[str, Any] = {"configurable": {"thread_id": request.conversation_id}}

        # Reprendre l'exécution du workflow
        logger.info("[RESPOND] Resuming workflow execution...")
        final_state = workflow_app.invoke(checkpoint, config)  # type: ignore[arg-type]

        # Extraire les informations finales
        result = final_state.get("result", "Workflow completed")
        status = final_state.get("status", "completed")
        project_id = final_state.get("project_id", "")

        logger.info(f"[RESPOND] Workflow completed with status: {status}")

        # Extraire les événements détaillés de l'agent depuis l'état final
        agent_events = final_state.get("agent_events", [])
        if agent_events:
            timeline_events.extend(agent_events)
            logger.info(f"[RESPOND] Extracted {len(agent_events)} agent events from state")

        # Ajouter l'événement WorkflowCompleteEvent
        complete_event = WorkflowCompleteEvent(
            result=result if result else "Workflow completed",
            status=status,
        )
        timeline_events.append(complete_event.model_dump())

        # Sauvegarder les événements dans l'historique de la timeline
        if project_id:
            try:
                storage = ProjectContextService()
                storage.save_timeline_events(project_id, timeline_events)
                logger.info(f"[RESPOND] Saved {len(timeline_events)} events to timeline history")
            except Exception as save_error:
                logger.error(f"Failed to save timeline events: {save_error}")

        # Nettoyer la session
        session_manager.delete_session(request.conversation_id)

        return ChatResponse(
            result=result,
            project_id=project_id,
            status=status,
            thread_id=None,
            impact_plan=None,
        )

    except Exception as e:
        logger.error(f"[RESPOND] Error resuming workflow: {e}", exc_info=True)

        # Ajouter un événement d'erreur
        error_event = ErrorEvent(
            error=str(e),
            details="An error occurred while resuming workflow",
        )
        timeline_events.append(error_event.model_dump())

        # Même en cas d'erreur, sauvegarder les événements si on a le checkpoint
        try:
            checkpoint = session_manager.get_checkpoint(request.conversation_id)
            project_id = checkpoint.get("project_id", "")
            if project_id:
                storage = ProjectContextService()
                storage.save_timeline_events(project_id, timeline_events)
                logger.info(
                    f"[RESPOND] Saved {len(timeline_events)} events to "
                    "timeline history (after error)"
                )
        except Exception as save_error:
            logger.error(f"Failed to save timeline events: {save_error}")

        # Nettoyer la session en cas d'erreur
        if session_manager.session_exists(request.conversation_id):
            session_manager.delete_session(request.conversation_id)

        raise HTTPException(
            status_code=500,
            detail=f"Error resuming workflow: {e}",
        ) from e


@app.get("/projects")
async def list_projects(
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """
    Liste tous les projets auxquels l'utilisateur a accès.

    Args:
        current_user: Utilisateur authentifié (injecté par la dépendance)

    Returns:
        JSONResponse avec la liste des identifiants de projets de l'utilisateur

    """
    storage = ProjectContextService()
    projects_dir = storage.base_path

    # Créer le répertoire s'il n'existe pas
    projects_dir.mkdir(parents=True, exist_ok=True)

    # Scanner les sous-répertoires et filtrer par accès utilisateur
    project_ids = []
    for entry in projects_dir.iterdir():
        if entry.is_dir():
            # Vérifier si l'utilisateur a accès à ce projet
            if storage.is_user_authorized_for_project(entry.name, current_user.id):
                project_ids.append(entry.name)

    # Trier par ordre alphabétique
    project_ids.sort()

    return JSONResponse(content=project_ids)


@app.post("/projects")
async def create_project(
    request: CreateProjectRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """
    Crée un nouveau projet et associe automatiquement l'utilisateur créateur.

    Args:
        request: Requête contenant l'identifiant du projet à créer
        current_user: Utilisateur authentifié (injecté par la dépendance)

    Returns:
        JSONResponse avec l'identifiant du projet créé

    Raises:
        HTTPException: Si le projet existe déjà
    """
    storage = ProjectContextService()
    user_service = UserService()

    try:
        # Créer le projet et associer l'utilisateur créateur
        storage.create_project(request.project_id, current_user.id)

        # Ajouter le projet à la liste des projets de l'utilisateur
        user_service.add_project_to_user(current_user.id, request.project_id)

        return JSONResponse(
            content={"project_id": request.project_id, "message": "Project created successfully"},
            status_code=201,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        ) from e


@app.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_project_user)],
) -> None:
    """
    Supprime un projet et toutes ses données associées.

    Args:
        project_id: Identifiant unique du projet à supprimer
        current_user: Utilisateur authentifié avec accès au projet

    Returns:
        Aucun contenu (code 204)

    Raises:
        HTTPException: Si le projet n'existe pas (404) ou si le project_id est invalide (400)
    """
    storage = ProjectContextService()
    user_service = UserService()

    try:
        # Récupérer tous les utilisateurs du projet
        user_ids = storage.get_project_users(project_id)

        # Supprimer le projet de la liste des projets de chaque utilisateur
        for user_id in user_ids:
            try:
                user_service.remove_project_from_user(user_id, project_id)
            except ValueError:
                # L'utilisateur n'existe plus, on continue
                pass

        # Supprimer le projet
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


@app.get("/projects/{project_id}/users")
async def get_project_users(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_project_user)],
) -> JSONResponse:
    """
    Liste les utilisateurs associés à un projet.

    Args:
        project_id: Identifiant unique du projet
        current_user: Utilisateur authentifié avec accès au projet

    Returns:
        JSONResponse avec la liste des utilisateurs (id et username)

    Raises:
        HTTPException: Si le projet n'existe pas
    """
    storage = ProjectContextService()
    user_service = UserService()

    try:
        user_ids = storage.get_project_users(project_id)

        # Récupérer les informations des utilisateurs
        users_info = []
        for user_id in user_ids:
            user = user_service.get_user_by_id(user_id)
            if user:
                users_info.append({
                    "id": user.id,
                    "username": user.username,
                })

        return JSONResponse(content=users_info)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found: {e}",
        ) from e


@app.post("/projects/{project_id}/users", status_code=201)
async def add_user_to_project(
    project_id: str,
    request: AddUserToProjectRequest,
    current_user: Annotated[User, Depends(get_current_project_user)],
) -> JSONResponse:
    """
    Ajoute un utilisateur à un projet (invitation).

    Args:
        project_id: Identifiant unique du projet
        request: Requête contenant le nom d'utilisateur à ajouter
        current_user: Utilisateur authentifié avec accès au projet

    Returns:
        JSONResponse avec un message de confirmation

    Raises:
        HTTPException: Si le projet ou l'utilisateur n'existe pas
    """
    storage = ProjectContextService()
    user_service = UserService()

    try:
        # Récupérer l'utilisateur par son username
        user_to_add = user_service.get_user_by_username(request.username)
        if user_to_add is None:
            raise HTTPException(
                status_code=404,
                detail=f"User '{request.username}' not found",
            )

        # Ajouter l'utilisateur au projet
        storage.add_user_to_project(project_id, user_to_add.id)

        # Ajouter le projet à la liste des projets de l'utilisateur
        user_service.add_project_to_user(user_to_add.id, project_id)

        return JSONResponse(
            content={
                "message": f"User '{request.username}' added to project '{project_id}'",
                "user_id": user_to_add.id,
            },
            status_code=201,
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found: {e}",
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        ) from e


@app.delete("/projects/{project_id}/users/{user_id}", status_code=204)
async def remove_user_from_project(
    project_id: str,
    user_id: str,
    current_user: Annotated[User, Depends(get_current_project_user)],
) -> None:
    """
    Retire un utilisateur d'un projet.

    Args:
        project_id: Identifiant unique du projet
        user_id: ID de l'utilisateur à retirer
        current_user: Utilisateur authentifié avec accès au projet

    Returns:
        Aucun contenu (code 204)

    Raises:
        HTTPException: Si le projet ou l'utilisateur n'existe pas
    """
    storage = ProjectContextService()
    user_service = UserService()

    try:
        # Retirer l'utilisateur du projet
        storage.remove_user_from_project(project_id, user_id)

        # Retirer le projet de la liste des projets de l'utilisateur
        user_service.remove_project_from_user(user_id, project_id)

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Project or user not found: {e}",
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        ) from e


@app.get("/projects/{project_id}/backlog")
async def get_project_backlog(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_project_user)],
) -> JSONResponse:
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


@app.get("/projects/{project_id}/schema")
async def get_project_schema(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_project_user)],
) -> JSONResponse:
    """
    Récupère le schéma de projet définissant les types de WorkItems et leurs champs.

    Args:
        project_id: Identifiant unique du projet
        current_user: Utilisateur authentifié avec accès au projet

    Returns:
        JSONResponse avec le schéma du projet (types de WorkItems et leurs champs)

    Raises:
        HTTPException: Si le projet n'existe pas ou n'a pas de schéma
    """
    storage = ProjectContextService()

    try:
        schema = storage.get_project_schema(project_id)
        return JSONResponse(content=schema.model_dump())
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Schema not found for project '{project_id}': {e}",
        ) from e


@app.get("/projects/{project_id}/diagrams")
async def get_project_diagrams(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_project_user)],
) -> JSONResponse:
    """
    Récupère tous les diagrammes d'un projet.

    Parcourt tous les work items du backlog et collecte tous les diagrammes
    qu'ils contiennent dans une liste plate.

    Args:
        project_id: Identifiant unique du projet

    Returns:
        JSONResponse avec la liste de tous les diagrammes du projet,
        chaque diagramme incluant également le work_item_id source

    Raises:
        HTTPException: Si le projet n'existe pas ou n'a pas de backlog
    """
    storage = ProjectContextService()

    try:
        work_items = storage.load_context(project_id)

        # Collecter tous les diagrammes de tous les work items
        all_diagrams = []
        for work_item in work_items:
            for diagram in work_item.diagrams:
                # Ajouter le diagramme avec une référence au work item source
                diagram_data = diagram.model_dump()
                diagram_data["work_item_id"] = work_item.id
                diagram_data["work_item_title"] = work_item.title
                diagram_data["work_item_type"] = work_item.type
                all_diagrams.append(diagram_data)

        logger.info(f"[GET_DIAGRAMS] Found {len(all_diagrams)} diagrams in project {project_id}")

        return JSONResponse(content=all_diagrams)

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Backlog not found for project '{project_id}': {e}",
        ) from e


@app.get("/projects/{project_id}/timeline")
async def get_project_timeline(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_project_user)],
) -> JSONResponse:
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
async def list_project_documents(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_project_user)],
) -> JSONResponse:
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
    current_user: Annotated[User, Depends(get_current_project_user)] = None,
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
async def delete_project_document(
    project_id: str,
    document_name: str,
    current_user: Annotated[User, Depends(get_current_project_user)],
) -> None:
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
    current_user: Annotated[User, Depends(get_current_project_user)],
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
    current_user: Annotated[User, Depends(get_current_project_user)],
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
    current_user: Annotated[User, Depends(get_current_project_user)],
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
    project_id: str,
    item_id: str,
    item_data: dict,
    current_user: Annotated[User, Depends(get_current_project_user)] = None,
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
async def validate_work_item(
    project_id: str,
    item_id: str,
    current_user: Annotated[User, Depends(get_current_project_user)],
) -> JSONResponse:
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
    project_id: str,
    item_id: str,
    current_user: Annotated[User, Depends(get_current_project_user)],
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


@app.post("/projects/{project_id}/work_items/{item_id}/generate-test-cases")
async def generate_test_cases_for_item(
    project_id: str,
    item_id: str,
    current_user: Annotated[User, Depends(get_current_project_user)],
) -> JSONResponse:
    """
    Génère les cas de test pour un WorkItem spécifique.

    Cette opération appelle directement l'agent de génération de cas de test
    sans passer par le graphe complet. Les cas de test sont créés en tant que
    nouveaux WorkItems de type test_case, liés au WorkItem parent.

    Args:
        project_id: Identifiant unique du projet
        item_id: Identifiant du WorkItem pour lequel générer les cas de test

    Returns:
        JSONResponse avec la liste des WorkItems de test créés

    Raises:
        HTTPException: Si le projet ou le WorkItem n'existe pas, ou en cas d'erreur
    """
    from agent4ba.ai import test_agent

    # Créer un état minimal pour l'agent
    state: dict[str, Any] = {
        "project_id": project_id,
        "intent_args": {"work_item_id": item_id},
        "thread_id": "",  # Pas de thread_id nécessaire pour un appel direct
    }

    try:
        # Appeler la fonction de génération de cas de test
        result = test_agent.generate_test_cases(state)

        # Vérifier le statut de la réponse
        if result.get("status") == "error":
            raise HTTPException(
                status_code=400,
                detail=result.get("result", "Error generating test cases"),
            )

        # Récupérer l'ImpactPlan
        impact_plan = result.get("impact_plan", {})
        new_items = impact_plan.get("new_items", [])

        if not new_items:
            raise HTTPException(
                status_code=500,
                detail="No test case work items generated by the agent",
            )

        # Ajouter les nouveaux WorkItems de test au backlog
        storage = ProjectContextService()

        # Charger le backlog existant
        work_items = storage.load_context(project_id)

        # Ajouter les nouveaux WorkItems de test
        created_test_cases = []
        for new_item_data in new_items:
            # Convertir le dict en WorkItem
            from agent4ba.core.models import WorkItem
            test_case_item = WorkItem(**new_item_data)
            work_items.append(test_case_item)
            created_test_cases.append(test_case_item.model_dump())

        # Sauvegarder le backlog mis à jour
        storage.save_backlog(project_id, work_items)

        return JSONResponse(
            content={
                "message": f"Successfully created {len(created_test_cases)} test case work items",
                "parent_id": item_id,
                "test_cases": created_test_cases,
            }
        )

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
            f"Error generating test cases for item {item_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error generating test cases: {e}",
        ) from e
