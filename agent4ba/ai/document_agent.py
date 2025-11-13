"""Document agent for extracting requirements from unstructured text."""

import json
import os
import uuid
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from litellm import completion

from agent4ba.api.event_queue import get_event_queue
from agent4ba.core.document_ingestion import DocumentIngestionService
from agent4ba.core.logger import setup_logger
from agent4ba.core.models import WorkItem
from agent4ba.core.storage import ProjectContextService
from agent4ba.core.workitem_utils import assign_sequential_ids

# Charger les variables d'environnement
load_dotenv()

# Configurer le logger
logger = setup_logger(__name__)


def load_extract_requirements_prompt() -> dict[str, Any]:
    """
    Charge le prompt d'extraction d'exigences depuis le fichier YAML.

    Returns:
        Dictionnaire contenant le prompt et les exemples
    """
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "extract_requirements.yaml"
    with prompt_path.open("r", encoding="utf-8") as f:
        result = yaml.safe_load(f)
        if not isinstance(result, dict):
            raise ValueError("Invalid prompt configuration")
        return result


def extract_requirements(state: Any) -> dict[str, Any]:
    """
    Extrait les exigences en utilisant RAG (Retrieval-Augmented Generation).

    Cette fonction :
    1. Charge la Vector Store FAISS du projet
    2. Utilise la requête utilisateur pour rechercher les documents pertinents
    3. Injecte ces documents comme contexte dans le prompt au LLM

    Args:
        state: État actuel du graphe contenant project_id et user_query

    Returns:
        Mise à jour de l'état avec impact_plan et status
    """
    logger.info("Extracting requirements using RAG...")

    # Récupérer le project_id et la requête utilisateur
    project_id = state.get("project_id", "")
    user_query = state.get("user_query", "")

    if not user_query or not user_query.strip():
        logger.warning("No user query provided")
        return {
            "status": "error",
            "result": "No user query provided for requirement extraction",
        }

    logger.info(f"User query: {user_query}")

    # Récupérer le thread_id et la queue d'événements
    thread_id = state.get("thread_id", "")
    event_queue = get_event_queue(thread_id) if thread_id else None

    # Initialiser la liste d'événements
    agent_events = []

    # Émettre l'événement AgentStart avec la reformulation
    start_event = {
        "type": "agent_start",
        "thought": f"Compris ! Je vais extraire les exigences pertinentes des documents en me basant sur votre recherche : « {user_query} ».",
        "agent_name": "DocumentAgent",
    }
    agent_events.append(start_event)
    if event_queue:
        event_queue.put(start_event)

    # Émettre le plan d'action
    plan_event = {
        "type": "agent_plan",
        "steps": [
            "Chargement de la Vector Store du projet",
            "Recherche des documents pertinents (RAG)",
            "Extraction des exigences via LLM",
            "Validation et construction de l'ImpactPlan",
        ],
        "agent_name": "DocumentAgent",
    }
    agent_events.append(plan_event)
    if event_queue:
        event_queue.put(plan_event)

    # Initialiser le service d'ingestion pour accéder au vectorstore
    vectorstore_run_id = str(uuid.uuid4())
    vectorstore_event = {
        "type": "tool_used",
        "tool_run_id": vectorstore_run_id,
        "tool_name": "Chargement du contexte",
        "tool_icon": "🗄️",
        "description": "Chargement de la base vectorielle des documents",
        "status": "running",
        "details": {},
    }
    agent_events.append(vectorstore_event)
    if event_queue:
        event_queue.put(vectorstore_event)

    try:
        ingestion_service = DocumentIngestionService(project_id)
        vectorstore = ingestion_service.get_vectorstore()

        # Compter le nombre de documents dans le vectorstore
        doc_count = len(vectorstore.docstore._dict) if hasattr(vectorstore, 'docstore') else 0
        logger.info(f"Vector store loaded successfully with {doc_count} documents")

        vectorstore_event_completed = {
            "type": "tool_used",
            "tool_run_id": vectorstore_run_id,
            "tool_name": "Chargement du contexte",
            "tool_icon": "🗄️",
            "description": "Chargement de la base vectorielle des documents",
            "status": "completed",
            "details": {"documents_loaded": doc_count},
        }
        agent_events[-1] = vectorstore_event_completed
        if event_queue:
            event_queue.put(vectorstore_event_completed)
    except FileNotFoundError as e:
        logger.warning(f"No vectorstore found: {e}")
        vectorstore_event_error = {
            "type": "tool_used",
            "tool_run_id": vectorstore_run_id,
            "tool_name": "Chargement du contexte",
            "tool_icon": "🗄️",
            "description": "Chargement de la base vectorielle des documents",
            "status": "error",
            "details": {"error": str(e)},
        }
        agent_events[-1] = vectorstore_event_error
        if event_queue:
            event_queue.put(vectorstore_event_error)
        return {
            "status": "error",
            "result": "Aucun document n'a été analysé pour ce projet. Veuillez d'abord uploader des documents.",
            "agent_events": agent_events,
        }
    except Exception as e:
        logger.error("Error loading vectorstore.", exc_info=True)
        vectorstore_event_error = {
            "type": "tool_used",
            "tool_run_id": vectorstore_run_id,
            "tool_name": "Chargement du contexte",
            "tool_icon": "🗄️",
            "description": "Chargement de la base vectorielle des documents",
            "status": "error",
            "details": {"error": str(e)},
        }
        agent_events[-1] = vectorstore_event_error
        if event_queue:
            event_queue.put(vectorstore_event_error)
        return {
            "status": "error",
            "result": f"Erreur lors du chargement du vectorstore: {e}",
            "agent_events": agent_events,
        }

    # Vérifier si un contexte de type "document" est fourni
    context = state.get("context", [])
    document_context = None
    if context:
        for ctx_item in context:
            if ctx_item.get("type") == "document":
                document_context = ctx_item.get("id")
                logger.info(f"Document context provided: {document_context}")
                break

    # Créer un retriever pour rechercher les documents pertinents
    # k=3 signifie qu'on récupère les 3 chunks les plus pertinents
    # Si un contexte document est fourni, on filtre par source
    search_kwargs = {"k": 3}
    if document_context:
        # Filtrer uniquement sur le document spécifié
        search_kwargs["filter"] = {"source": document_context}
        logger.info(f"Applying document filter: {document_context}")

    retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)
    logger.info(f"Retriever created with k=3{' and document filter' if document_context else ''}")

    # Émettre l'événement de recherche RAG
    rag_run_id = str(uuid.uuid4())
    rag_event = {
        "type": "tool_used",
        "tool_run_id": rag_run_id,
        "tool_name": "Recherche RAG",
        "tool_icon": "🔍",
        "description": "Recherche des chunks de documents pertinents",
        "status": "running",
        "details": {},
    }
    agent_events.append(rag_event)
    if event_queue:
        event_queue.put(rag_event)

    # Récupérer les documents pertinents
    try:
        retrieved_docs = retriever.invoke(user_query)
        logger.info(f"Retrieved {len(retrieved_docs)} relevant chunks")
        rag_event_completed = {
            "type": "tool_used",
            "tool_run_id": rag_run_id,
            "tool_name": "Recherche RAG",
            "tool_icon": "🔍",
            "description": "Recherche des chunks de documents pertinents",
            "status": "completed",
            "details": {"chunks_retrieved": len(retrieved_docs)},
        }
        agent_events[-1] = rag_event_completed
        if event_queue:
            event_queue.put(rag_event_completed)
    except Exception as e:
        logger.error("Error retrieving documents.", exc_info=True)
        rag_event_error = {
            "type": "tool_used",
            "tool_run_id": rag_run_id,
            "tool_name": "Recherche RAG",
            "tool_icon": "🔍",
            "description": "Recherche des chunks de documents pertinents",
            "status": "error",
            "details": {"error": str(e)},
        }
        agent_events[-1] = rag_event_error
        if event_queue:
            event_queue.put(rag_event_error)
        return {
            "status": "error",
            "result": f"Erreur lors de la récupération des documents: {e}",
            "agent_events": agent_events,
        }

    # Formater le contexte récupéré
    context_chunks = []
    for i, doc in enumerate(retrieved_docs, 1):
        source = doc.metadata.get("source", "Unknown")
        page = doc.metadata.get("page", "?")
        context_chunks.append(f"[Chunk {i} - Source: {source}, Page: {page}]\n{doc.page_content}")

    context = "\n\n---\n\n".join(context_chunks)
    logger.info(f"Context prepared: {len(context)} characters")

    # Charger le contexte du projet (backlog existant)
    storage = ProjectContextService()
    try:
        existing_items = storage.load_context(project_id)
        backlog_summary = f"Backlog actuel avec {len(existing_items)} work items"
        logger.info(f"Loaded {len(existing_items)} existing work items")
    except FileNotFoundError:
        existing_items = []
        backlog_summary = "Nouveau projet sans backlog existant"
        logger.info("No existing backlog found")

    # Charger le prompt
    prompt_config = load_extract_requirements_prompt()

    # Préparer le prompt utilisateur avec le contexte récupéré
    user_prompt = prompt_config["user_prompt_template"].format(
        context=context,
        query=user_query,
        backlog_summary=backlog_summary,
    )

    # Récupérer le modèle depuis l'environnement
    model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    logger.info(f"Using model: {model}")

    # Émettre l'événement d'appel LLM
    llm_run_id = str(uuid.uuid4())
    # Créer un résumé court du prompt pour les détails
    prompt_preview = user_prompt[:200] + "..." if len(user_prompt) > 200 else user_prompt
    llm_event = {
        "type": "tool_used",
        "tool_run_id": llm_run_id,
        "tool_name": "Appel LLM",
        "tool_icon": "🧠",
        "description": f"Extraction des exigences avec {model}",
        "status": "running",
        "details": {
            "model": model,
            "temperature": temperature,
            "prompt_preview": prompt_preview,
        },
    }
    agent_events.append(llm_event)
    if event_queue:
        event_queue.put(llm_event)

    try:
        # Appeler le LLM
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": prompt_config["system_prompt"]},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )

        # Extraire la réponse
        response_text = response.choices[0].message.content

        logger.info(f"LLM response received: {len(response_text)} characters")

        # Créer un résumé de la réponse
        response_preview = response_text[:300] + "..." if len(response_text) > 300 else response_text

        # Mettre à jour le statut
        llm_event_completed = {
            "type": "tool_used",
            "tool_run_id": llm_run_id,
            "tool_name": "Appel LLM",
            "tool_icon": "🧠",
            "description": f"Extraction des exigences avec {model}",
            "status": "completed",
            "details": {
                "model": model,
                "temperature": temperature,
                "prompt_preview": prompt_preview,
                "response_length": len(response_text),
                "response_preview": response_preview,
            },
        }
        agent_events[-1] = llm_event_completed
        if event_queue:
            event_queue.put(llm_event_completed)

        # Parser la réponse JSON
        work_items_data = json.loads(response_text)

        if not isinstance(work_items_data, list):
            raise ValueError("LLM response is not a list of work items")

        logger.info(f"Extracted {len(work_items_data)} work items")

        # Assigner des ID séquentiels uniques basés sur le préfixe du projet
        work_items_data = assign_sequential_ids(project_id, existing_items, work_items_data)
        logger.info("Assigned sequential IDs starting with project prefix")

        # Valider et convertir en WorkItem
        new_items = []
        for item_data in work_items_data:
            # Ajouter le project_id
            item_data["project_id"] = project_id
            # Marquer comme généré par l'IA
            item_data["validation_status"] = "pending_validation"

            # Créer le WorkItem (validation Pydantic)
            work_item = WorkItem(**item_data)
            new_items.append(work_item)

            logger.info(f"  - {work_item.type}: {work_item.title} (ID: {work_item.id})")

        # Construire l'ImpactPlan
        impact_plan = {
            "new_items": [item.model_dump() for item in new_items],
            "modified_items": [],
            "deleted_items": [],
        }

        logger.info("ImpactPlan created successfully")
        logger.info(f"- {len(new_items)} new items")
        logger.info("Workflow paused, awaiting human approval")

        # Émettre l'événement de construction de l'ImpactPlan
        plan_build_run_id = str(uuid.uuid4())
        plan_build_event = {
            "type": "tool_used",
            "tool_run_id": plan_build_run_id,
            "tool_name": "Construction ImpactPlan",
            "tool_icon": "📋",
            "description": "Création du plan d'impact avec les exigences extraites",
            "status": "completed",
            "details": {"new_items_count": len(new_items)},
        }
        agent_events.append(plan_build_event)
        if event_queue:
            event_queue.put(plan_build_event)

        return {
            "impact_plan": impact_plan,
            "status": "awaiting_approval",
            "result": f"Extracted {len(new_items)} work items from document",
            "agent_events": agent_events,
        }

    except json.JSONDecodeError as e:
        logger.error("Error parsing JSON.", exc_info=True)
        llm_event_error = {
            "type": "tool_used",
            "tool_run_id": llm_run_id,
            "tool_name": "Appel LLM",
            "tool_icon": "🧠",
            "description": f"Extraction des exigences avec {model}",
            "status": "error",
            "details": {
                "model": model,
                "error": str(e),
            },
        }
        agent_events[-1] = llm_event_error
        if event_queue:
            event_queue.put(llm_event_error)
        return {
            "status": "error",
            "result": f"Failed to parse LLM response as JSON: {e}",
            "agent_events": agent_events,
        }
    except Exception as e:
        logger.error("Error during requirement extraction.", exc_info=True)
        if agent_events and agent_events[-1].get("status") == "running":
            error_event = agent_events[-1]
            error_event["status"] = "error"
            error_event["details"] = error_event.get("details", {})
            error_event["details"]["error"] = str(e)
            if event_queue:
                event_queue.put(error_event)
        return {
            "status": "error",
            "result": f"Failed to extract requirements: {e}",
            "agent_events": agent_events,
        }
